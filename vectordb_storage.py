import fitz
import os
from uuid import uuid4
from tqdm import tqdm
from pinecone import Pinecone, ServerlessSpec
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = "processed_pdfs.log"

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "transcripts-jina"

# Check if index exists, create if not
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=768,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print("🆕 Index created successfully!")
else:
    print("✅ Index already exists. Skipping recreation.")

index = pc.Index(INDEX_NAME)

def load_processed_pdfs():
    """Load the set of already processed PDFs from log file."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return set(line.strip() for line in f.readlines())
    return set()

def update_log_file(processed_pdfs):
    """Append newly processed PDFs to the log file."""
    with open(LOG_FILE, "a") as f:
        for pdf in processed_pdfs:
            f.write(pdf + "\n")

def extract_text_by_page(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    
    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": page_num + 1, "text": text})
    
    return pages

def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= text_len:
            break
        start += chunk_size - overlap
    return chunks

def get_jina_embeddings(texts, batch_size=32):
    if not texts:
        return []

    url = "https://api.jina.ai/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('JINA_API_KEY')}"
    }

    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        data = {
            "model": "jina-embeddings-v2-base-en",
            "input": batch
        }
        
        max_retries = 5
        for retry in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code == 429:
                    time.sleep(2 ** retry)
                    continue
                    
                response.raise_for_status()
                json_resp = response.json()
                
                # ensure ordering
                batch_embeddings = [None] * len(batch)
                for item in json_resp["data"]:
                    batch_embeddings[item["index"]] = item["embedding"]
                
                all_embeddings.extend(batch_embeddings)
                break
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429 and retry < max_retries - 1:
                    time.sleep(2 ** retry)
                    continue
                print(f"❌ Error fetching embeddings from Jina API: {e}")
                all_embeddings.extend([None] * len(batch))
                break
            except Exception as e:
                print(f"❌ Error fetching embeddings from Jina API: {e}")
                all_embeddings.extend([None] * len(batch))
                break

    return all_embeddings

def store_pdfs_in_pinecone(pdf_directory):
    vectors = []
    pdf_files = [f for f in os.listdir(pdf_directory) if f.endswith(".pdf")]

    processed_pdfs = load_processed_pdfs()

    new_processed_pdfs = set()

    for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
        company_name = os.path.splitext(pdf_file)[0]

        if pdf_file in processed_pdfs:
            print(f"⏭️ Skipping {pdf_file}, already logged as processed.")
            continue

        pdf_path = os.path.join(pdf_directory, pdf_file)
        pages = extract_text_by_page(pdf_path)

        chunks_info = []
        for page in pages:
            page_chunks = chunk_text(page["text"], chunk_size=500, overlap=50)
            for chunk in page_chunks:
                chunks_info.append({"text": chunk, "page": page["page"]})

        chunk_texts = [chunk["text"] for chunk in chunks_info]
        
        if not chunk_texts:
            new_processed_pdfs.add(pdf_file)
            continue
            
        embeddings = get_jina_embeddings(chunk_texts)

        for _i, chunk_info in enumerate(chunks_info):
            if _i >= len(embeddings) or not embeddings[_i]:
                continue
                
            text = chunk_info["text"]
            page_num = chunk_info["page"]
            embedding = embeddings[_i]

            vectors.append({
                "id": str(uuid4()),
                "values": embedding,
                "metadata": {"company": company_name, "text": text, "page": page_num}
            })

        new_processed_pdfs.add(pdf_file)

    if vectors:
        index.upsert(vectors=vectors)
        update_log_file(new_processed_pdfs)
        print("✅ New data stored in Pinecone successfully!")
    else:
        print("✅ No new PDFs to process.")

def query_db(company_name, query_text, top_k=5):
    embedding_res = get_jina_embeddings([query_text])
    if not embedding_res:
         return []
    
    embedding = embedding_res[0]

    search_result = index.query(
        vector=embedding,
        top_k=top_k,
        filter={"company": {"$eq": company_name}},
        include_metadata=True
    )

    results = [{"text": match.metadata["text"], "page": match.metadata["page"], "score": match.score} for match in search_result.matches]
    return results

if __name__ == "__main__":
    pdf_directory = "data/transcripts"
    store_pdfs_in_pinecone(pdf_directory)

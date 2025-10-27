import fitz
import os
from uuid import uuid4
from tqdm import tqdm
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
import time
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = "processed_pdfs.log"
model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "transcripts"

# Check if index exists, create if not
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=model.get_sentence_embedding_dimension(),
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

        for page in pages:
            text = page["text"]
            page_num = page["page"]
            embedding = model.encode(text)

            vectors.append({
                "id": str(uuid4()),
                "values": embedding.tolist(),
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
    embedding = model.encode(query_text)

    search_result = index.query(
        vector=embedding.tolist(),
        top_k=top_k,
        filter={"company": {"$eq": company_name}},
        include_metadata=True
    )

    results = [{"text": match.metadata["text"], "page": match.metadata["page"], "score": match.score} for match in search_result.matches]
    return results

if __name__ == "__main__":
    pdf_directory = "data/transcripts"
    store_pdfs_in_pinecone(pdf_directory)

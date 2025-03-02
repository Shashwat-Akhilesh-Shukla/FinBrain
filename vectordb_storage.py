import fitz
import os
from uuid import uuid4
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.http import exceptions
from qdrant_client.models import PointStruct, Distance, VectorParams, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

LOG_FILE = "processed_pdfs.log"
model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')
client = QdrantClient("http://localhost:6333")
COLLECTION_NAME = "transcripts"

try:
    client.get_collection(COLLECTION_NAME)
    print("✅ Collection already exists. Skipping recreation.")
except exceptions.UnexpectedResponse:
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=model.get_sentence_embedding_dimension(), distance=Distance.COSINE),
    )
    print("🆕 Collection created successfully!")

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

def store_pdfs_in_qdrant(pdf_directory):
    points = []
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

            points.append(
                PointStruct(
                    id=str(uuid4()),
                    vector=embedding.tolist(),
                    payload={"company": company_name, "text": text, "page": page_num}
                )
            )

        new_processed_pdfs.add(pdf_file)

    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        update_log_file(new_processed_pdfs)
        print("✅ New data stored in Qdrant successfully!")
    else:
        print("✅ No new PDFs to process.")

def query_db(company_name, query_text, top_k=5):
    embedding = model.encode(query_text)

    search_result = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding.tolist(),
        limit=top_k,
        query_filter=Filter(
            must=[FieldCondition(key="company", match=MatchValue(value=company_name))]
        ),
    )

    results = [{"text": hit.payload["text"], "page": hit.payload["page"], "score": hit.score} for hit in search_result]
    return results

if __name__ == "__main__":
    pdf_directory = "/Users/shashwatshukla/Desktop/Personal/RAGPROJECT/data/transcripts"
    store_pdfs_in_qdrant(pdf_directory)
    # company = "bhartiairtel"
    # query_text = "consolidated revenue?"
    # results = query_db(company, query_text)

    # print("\n🔍 Query Results:")
    # for res in results:
    #     print(f"Page: {res['page']} | Score: {res['score']:.2f} | Snippet: {res['text']}")

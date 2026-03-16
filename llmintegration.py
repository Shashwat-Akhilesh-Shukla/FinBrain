from vectordb_storage import store_pdfs_in_pinecone, query_db
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
vector_op = []

if __name__ == "__main__":
    company = "bhartiairtel"
    query_text = "revenue, ebidta, profit, net_profit"
    results = query_db(company, query_text)

    print("\n🔍 Query Results:")
    for res in results:
        vector_op.append(res)

    # Configure Gemini API
    genai.configure(api_key=os.getenv("API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash")

    query = "extract information relevant to revenue and ebidta in structured format"
    prompt = f"Document content:\n{vector_op}\n\nUser query: {query}"

    try:
        response = model.generate_content(prompt)
        print(response.text)
    except Exception as exc:
        print(f"Exception: {exc}")
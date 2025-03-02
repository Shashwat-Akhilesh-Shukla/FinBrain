from vectordb_storage import query_db
from krutrim_cloud import KrutrimCloud
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

client = KrutrimCloud(api_key=os.environ.get("API_KEY"))
model_name = "DeepSeek-R1"

query = "extract information relevant to revenue and ebidta in structured format"
prompt = f"Document content:\n{vector_op}\n\nUser query: {query}"

messages = [
    {"role": "user", "content": prompt}
]
try:
    response_stream = client.chat.completions.create(model=model_name, messages=messages)
    print(response_stream.choices[0].message.content)
except Exception as exc:
    print(f"Exception: {exc}")
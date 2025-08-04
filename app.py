import streamlit as st
import os
from vectordb_storage import store_pdfs_in_qdrant, query_db
from krutrim_cloud import KrutrimCloud
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Financial RAG Pipeline", layout="wide")
st.title("📊 Financial AI Analyst")

# Sidebar: PDF Upload & Processing
st.sidebar.header("📂 Upload PDFs")
uploaded_files = st.sidebar.file_uploader("Upload financial reports (PDF)", type="pdf", accept_multiple_files=True)

pdf_directory = "data"
os.makedirs(pdf_directory, exist_ok=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_path = os.path.join(pdf_directory, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
    st.sidebar.success(f"{len(uploaded_files)} PDFs uploaded successfully!")
    if st.sidebar.button("🔄 Process PDFs"):
        store_pdfs_in_qdrant(pdf_directory)
        st.sidebar.success("✅ PDFs stored in Qdrant successfully!")

# Main Section: Querying
st.header("🔍 Query Financial Reports")

# User Inputs
company = st.text_input("🏢 Enter Company Name:", "bhartiairtel")
query_text = st.text_area("📝 Enter Search Query (for Vector DB):", "revenue, EBITDA, profit, net profit")
ai_query = st.text_area("🤖 Customize AI Query (for DeepSeek):", "Extract revenue and EBITDA insights in a structured table.")

if st.button("🔍 Get Financial Insights"):
    if not company or not query_text:
        st.warning("⚠️ Please enter both a company name and a query.")
    else:
        st.info(f"Processing query for '{company}'...")

        # Query Qdrant (Vector DB)
        results = query_db(company, query_text)

        if not results:
            st.warning("No relevant data found in reports.")
        else:
            # Extract relevant content from results
            document_content = "\n\n".join([res["text"] for res in results])

            # AI Processing (DeepSeek)
            client = KrutrimCloud(api_key=os.getenv("API_KEY"))
            model_name = "DeepSeek-R1"

            prompt = f"Document content:\n{document_content}\n\nUser query: {ai_query}"
            messages = [{"role": "user", "content": prompt}]

            try:
                response_stream = client.chat.completions.create(model=model_name, messages=messages)
                structured_output = response_stream.choices[0].message.content
                st.subheader("📊 AI-Generated Financial Summary")
                st.write(structured_output)

                # (Optional) Debugging: Expandable section for raw vector DB results
                with st.expander("🛠️ Debug: View Raw Vector DB Matches"):
                    for res in results:
                        st.markdown(f"**Page {res['page']}** | Score: {res['score']:.2f}")
                        st.write(res["text"])
            except Exception as exc:
                st.error(f"❌ Error fetching AI response: {exc}")

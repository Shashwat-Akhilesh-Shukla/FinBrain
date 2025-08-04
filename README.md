# 📊 FinBrain — AI Financial Analyst

FinBrain is an AI-powered financial document analysis tool that distills insights from earnings reports, investor call transcripts, and financial statements into actionable summaries.

It fuses **Retrieval-Augmented Generation (RAG)** with **Qdrant** for high-performance vector search and leverages **DeepSeek R1 via Krutrim Cloud API** to generate structured financial intelligence.

Built with **Streamlit** for an intuitive interface and containerized with **Docker**, FinBrain makes it effortless to upload PDFs, query them, and extract deep financial insights — all within seconds.

---

## 🚀 Demo

Watch FinBrain in action:

[![Watch the demo](https://www.loom.com/share/2264c7d9bae844ff8d9ea22fd06fe25a?sid=60dc4659-647d-48ec-b4a6-9df2b8fe9a0c)

---

## 🧠 How It Works

### 1. Document Ingestion & Vectorization
- Upload PDFs of financial reports.
- Each page is extracted and embedded using `all-MiniLM-L12-v2` via **Sentence Transformers**.
- Embeddings are stored in **Qdrant** under company-specific payloads.

### 2. Vector Search
- Query terms like `"revenue, EBITDA, profit"` search the vector DB for semantically similar paragraphs.

### 3. AI-Powered Summarization
- DeepSeek R1 via Krutrim API processes top-matching results and generates a structured summary (e.g., financial tables).

---

## 🧩 Tech Stack

| Layer        | Technology                                |
|--------------|--------------------------------------------|
| Interface    | Streamlit                                  |
| Embeddings   | Sentence-Transformers (`MiniLM-L12-v2`)    |
| Vector DB    | Qdrant (self-hosted)                       |
| LLM API      | DeepSeek R1 via Krutrim Cloud              |
| Parsing PDFs | PyMuPDF (`fitz`)                           |
| Container    | Docker                                     |

---

## 📦 Local Setup

### Prerequisites

- Python 3.9+
- Docker
- Krutrim API Key (set in `.env`)

### 1. Clone the Repository

```bash
git clone https://github.com/Shashwat-Akhilesh-Shukla/FinBrain.git
cd FinBrain
````

### 2. Configure Environment Variables

Create a `.env` file with the following:

```env
API_KEY=your_krutrim_api_key_here
```

### 3. Start Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the App

```bash
streamlit run app.py
```

---

## 🧪 Example Workflow

1. Upload multiple PDFs of company earnings reports.
2. Click **"Process PDFs"** — vectors are stored in Qdrant.
3. Enter a semantic query like `"net profit"`.
4. Customize the AI prompt or use the default.
5. Click **"Get Financial Insights"** and get a structured, AI-generated summary.

---

## 🔍 Example Use Cases

* **Investor Research**: Pull out financial KPIs in seconds.
* **Competitive Intelligence**: Compare performance metrics across firms.
* **Earnings Call Highlights**: Summarize long transcripts instantly.
* **Due Diligence**: Rapidly assess financial health for investment.

---

## 🗂 Directory Structure

```
.
├── app.py                # Streamlit frontend
├── llmintegration.py     # Script to test LLM response separately
├── vectordb_storage.py   # Qdrant integration and PDF processing
├── krutrim_cloud.py      # Krutrim API wrapper
├── data/                 # Uploaded PDF storage
├── .env                  # API key config
├── requirements.txt
└── Dockerfile (coming soon)
```

---

## 🤝 Contributing

Open to PRs!
Fix something, improve the UX, or optimize the AI prompt chaining — but don’t bloat the repo.

---

## 🛡 License

MIT License — Use freely. Break it, fork it, profit from it.
- Deploy instructions for Hugging Face or Streamlit Cloud
```

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import shutil
import logging
import asyncio
from vectordb_storage import store_pdfs_in_pinecone, query_db
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("finbrain")

# ── Gemini – configure ONCE at startup ───────────────────────────────────────
_SYSTEM_INSTRUCTION = (
    "You are a senior financial analyst AI. "
    "Always respond using strict, well-structured Markdown formatting. "
    "Use the following rules:\n"
    "- Use ## for section headers.\n"
    "- Use Markdown tables (with header row and separator row) wherever comparative or tabular data is present.\n"
    "- Use bullet points (-) for lists of insights or observations.\n"
    "- Use **bold** to highlight key metrics (revenue, EBITDA, margins, growth rates).\n"
    "- Never output raw pipe characters as prose; always format them as proper Markdown tables.\n"
    "- Keep your response concise and professional. Do not include disclaimers or filler text."
)

genai.configure(api_key=os.getenv("API_KEY"))
_gemini_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=_SYSTEM_INSTRUCTION,
)
_generation_config = genai.GenerationConfig(
    temperature=0.2,
    response_mime_type="text/plain",
)
log.info("[STARTUP] Gemini model ready.")

app = FastAPI(title="Financial RAG Pipeline API")

# Ensure static and data directories exist
os.makedirs("static", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

class QueryRequest(BaseModel):
    company: str
    query_text: str
    ai_query: str

@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    pdf_directory = "data"
    
    saved_files = []
    for file in files:
        if not file.filename.endswith(".pdf"):
            continue
            
        file_path = os.path.join(pdf_directory, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file.filename)
        
    if not saved_files:
        raise HTTPException(status_code=400, detail="No valid PDF files uploaded")
        
    log.info("[UPLOAD] Saved files: %s", saved_files)
    try:
        # Offload blocking Jina + Pinecone upsert to thread pool
        log.info("[UPLOAD] Calling store_pdfs_in_pinecone('%s')", pdf_directory)
        await asyncio.to_thread(store_pdfs_in_pinecone, pdf_directory)
        log.info("[UPLOAD] Pinecone ingestion complete for %d file(s)", len(saved_files))
        return {"message": f"Successfully uploaded and processed {len(saved_files)} files to Pinecone."}
    except Exception as e:
        log.exception("[UPLOAD] Error during Pinecone ingestion")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def process_query(req: QueryRequest):
    log.info("[QUERY] Received: company=%r  query_text=%r", req.company, req.query_text)

    if not req.company or not req.query_text:
        raise HTTPException(status_code=400, detail="Missing company name or query string")

    # Offload blocking Jina embed + Pinecone query to thread pool
    results = await asyncio.to_thread(query_db, req.company, req.query_text)
    log.info("[QUERY] query_db returned %d result(s)", len(results) if results else 0)

    if not results:
        raise HTTPException(status_code=404, detail="No relevant data found in reports.")

    document_content = "\n\n".join([res["text"] for res in results])

    prompt = (
        f"## Source Document Context\n\n{document_content}\n\n"
        f"## Analytical Instruction\n\n{req.ai_query}"
    )

    try:
        # Offload blocking Gemini network call to thread pool
        response = await asyncio.to_thread(
            _gemini_model.generate_content, prompt, _generation_config
        )
        log.info("[QUERY] Gemini response received, length=%d chars", len(response.text))
        return {
            "answer": response.text,
            "raw_matches": results
        }
    except Exception as exc:
        log.exception("[QUERY] Error generating AI response")
        raise HTTPException(status_code=500, detail=f"Error generating AI response: {exc}")

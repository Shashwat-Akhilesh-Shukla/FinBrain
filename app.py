from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import shutil
import logging
from vectordb_storage import store_pdfs_in_pinecone, query_db
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Debug Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("finbrain")

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
        # Run process that chunks and uploads matching texts into Pinecone
        log.debug("[UPLOAD] Calling store_pdfs_in_pinecone('%s')", pdf_directory)
        store_pdfs_in_pinecone(pdf_directory)
        log.info("[UPLOAD] Pinecone ingestion complete for %d file(s)", len(saved_files))
        return {"message": f"Successfully uploaded and processed {len(saved_files)} files to Pinecone."}
    except Exception as e:
        log.exception("[UPLOAD] Error during Pinecone ingestion")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def process_query(req: QueryRequest):
    log.info("[QUERY] Received: company=%r  query_text=%r", req.company, req.query_text)
    log.debug("[QUERY] ai_query=%r", req.ai_query)

    if not req.company or not req.query_text:
        raise HTTPException(status_code=400, detail="Missing company name or query string")
        
    # Search Vector DB for context
    log.debug("[QUERY] Calling query_db ...")
    results = query_db(req.company, req.query_text)
    log.info("[QUERY] query_db returned %d result(s)", len(results) if results else 0)

    if results:
        for i, r in enumerate(results):
            log.debug("[QUERY] Match #%d  page=%s  score=%s  text_preview=%r",
                      i, r.get('page'), r.get('score'), r.get('text', '')[:120])
    
    if not results:
        raise HTTPException(status_code=404, detail="No relevant data found in reports.")
        
    document_content = "\n\n".join([res["text"] for res in results])
    log.debug("[QUERY] Combined context length: %d chars", len(document_content))
    
    # Init Gemini and execute generative lookup
    genai.configure(api_key=os.getenv("API_KEY"))

    system_instruction = (
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

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_instruction,
    )

    prompt = (
        f"## Source Document Context\n\n{document_content}\n\n"
        f"## Analytical Instruction\n\n{req.ai_query}"
    )
    log.debug("[QUERY] Prompt length: %d chars", len(prompt))

    generation_config = genai.GenerationConfig(
        temperature=0.2,
        response_mime_type="text/plain",
    )

    try:
        log.debug("[QUERY] Calling Gemini model ...")
        response = model.generate_content(prompt, generation_config=generation_config)
        log.info("[QUERY] Gemini response received, length=%d chars", len(response.text))
        log.debug("[QUERY] RAW LLM OUTPUT:\n%s", response.text)
        return {
            "answer": response.text,
            "raw_matches": results
        }
    except Exception as exc:
        log.exception("[QUERY] Error generating AI response")
        raise HTTPException(status_code=500, detail=f"Error generating AI response: {exc}")

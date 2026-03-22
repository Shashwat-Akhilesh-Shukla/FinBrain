from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import shutil
from vectordb_storage import store_pdfs_in_pinecone, query_db
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

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
        
    try:
        # Run process that chunks and uploads matching texts into Pinecone
        store_pdfs_in_pinecone(pdf_directory)
        return {"message": f"Successfully uploaded and processed {len(saved_files)} files to Pinecone."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def process_query(req: QueryRequest):
    if not req.company or not req.query_text:
        raise HTTPException(status_code=400, detail="Missing company name or query string")
        
    # Search Vector DB for context
    results = query_db(req.company, req.query_text)
    
    if not results:
        raise HTTPException(status_code=404, detail="No relevant data found in reports.")
        
    document_content = "\n\n".join([res["text"] for res in results])
    
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

    generation_config = genai.GenerationConfig(
        temperature=0.2,
        response_mime_type="text/plain",
    )

    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        return {
            "answer": response.text,
            "raw_matches": results
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating AI response: {exc}")

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.agent import ResearchGuardrailAgent
from src.attention.router import router as attention_router

app = FastAPI(
    title="Confidential Research Similarity & Plagiarism Checker",
    description="Secure, local-first API to check plagiarism and semantic similarity against life sciences databases.",
    version="1.0.0"
)

# Enable CORS for local development UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register our research attention router
app.include_router(attention_router)

# Mount static files directory for local resources (like D3.js and styles)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize our agent locally
# Note: On startup, this will load spaCy and SentenceTransformers
agent = ResearchGuardrailAgent()

@app.post("/api/analyze")
async def analyze_file(file: UploadFile = File(...)):
    """
    Upload a document (PDF, DOCX, TXT) to perform plagiarism and semantic checks.
    The uploaded file is processed completely in memory and never stored on disk.
    """
    allowed_extensions = {".pdf", ".docx", ".doc", ".txt"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
        )
        
    try:
        # Read file completely in memory
        content = await file.read()
        
        # Run local agent analysis
        report = agent.analyze_document(content, file.filename)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )

@app.get("/", response_class=HTMLResponse)
def get_portal_hub():
    """Serves the portal landing Pre-page."""
    portal_path = os.path.join(os.path.dirname(__file__), "static", "pre_page.html")
    if not os.path.exists(portal_path):
        raise HTTPException(status_code=404, detail="Portal pre-page UI file not found.")
    with open(portal_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/plagiarism", response_class=HTMLResponse)
def get_plagiarism_checker():
    """Serves the plagiarism checker dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    if not os.path.exists(dashboard_path):
        raise HTTPException(status_code=404, detail="Dashboard UI file not found.")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/attention", response_class=HTMLResponse)
def get_attention_dashboard():
    """Serves the research attention analytics dashboard."""
    attention_path = os.path.join(os.path.dirname(__file__), "static", "attention.html")
    if not os.path.exists(attention_path):
        raise HTTPException(status_code=404, detail="Attention dashboard UI file not found.")
    with open(attention_path, "r", encoding="utf-8") as f:
        return f.read()

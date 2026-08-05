import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from src.agent import ResearchGuardrailAgent

app = FastAPI(
    title="Confidential Research Similarity & Plagiarism Checker",
    description="Secure, local-first API to check plagiarism and semantic similarity against academic databases.",
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
def get_dashboard():
    """Serves the front-end dashboard UI."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    if not os.path.exists(dashboard_path):
        raise HTTPException(status_code=404, detail="Dashboard UI file not found.")
        
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return f.read()

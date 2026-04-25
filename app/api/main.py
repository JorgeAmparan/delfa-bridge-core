from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from app.api.routers import documents, search, governance, trail, connectors, billing, chat
from app.api.auth import router as auth_router
import os

load_dotenv()

app = FastAPI(
    title="Delfa Bridge API",
    description="Intelligent Middleware for Enterprise AI | Powered by Panohayan™",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — configurable via ALLOWED_ORIGINS en .env
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(governance.router)
app.include_router(trail.router)
app.include_router(connectors.router)
app.include_router(billing.router)
app.include_router(chat.router)

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    return {
        "product": "Delfa Bridge",
        "architecture": "Panohayan™",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "org": os.getenv("ORG_ID")}


@app.get("/demo")
async def demo_portal():
    demo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "demo", "index.html")
    return FileResponse(demo_path, media_type="text/html")


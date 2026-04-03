from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import documents, search, governance, trail
from dotenv import load_dotenv
from app.api.routers import documents, search, governance, trail, connectors
from app.api.routers import documents, search, governance, trail, connectors, billing
import os

load_dotenv()

app = FastAPI(
    title="Delfa Bridge API",
    description="Intelligent Middleware for Enterprise AI | Powered by Panohayan™",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — permite conexión desde Lovable y cualquier frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(governance.router)
app.include_router(trail.router)
app.include_router(connectors.router)
app.include_router(billing.router)

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


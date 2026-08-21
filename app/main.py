import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine, Base
from .routers import public, admin
from .supabase_storage import ensure_storage_infrastructure

# Initialize FastAPI application
app = FastAPI(
    title="Cepsa Tiles & Bathware API",
    description="REST API for Cepsa catalog, public search, inquiry submissions, and Owner Admin Panel.",
    version="1.0.0"
)

# Enable CORS for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(public.router)
app.include_router(admin.router)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE inquiries ADD COLUMN inquiry_type VARCHAR(30) DEFAULT 'customer'"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE inquiries ADD COLUMN product_name VARCHAR(150)"))
            conn.commit()
        except Exception:
            pass
        try:
            ensure_storage_infrastructure()
        except Exception as e:
            print(f"[Supabase Storage] Bootstrap error: {e}")

@app.get("/")
def read_root():
    return {
        "brand": "Cepsa Tiles & Bathware",
        "status": "Online",
        "docs": "/docs",
        "public_products": "/api/v1/public/products",
        "admin_login": "/api/v1/admin/login"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

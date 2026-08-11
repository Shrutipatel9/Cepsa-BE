import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, Base
from .routers import public, admin

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploaded media directory with no-cache headers for instant image updates
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app.mount("/uploads", NoCacheStaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(public.router)
app.include_router(admin.router)

from sqlalchemy import text

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

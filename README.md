# Cepsa Backend (Python / FastAPI)

Backend API service for Cepsa Tiles & Bathware Showcase and Management Portal.

## Architecture
- **Framework**: Python 3.10+ with FastAPI
- **Database**: SQLite (SQLAlchemy ORM) / PostgreSQL ready
- **Authentication**: JWT token-based auth for Admin endpoints
- **Image Storage**: Local media upload directory / S3 compatible
- **API Features**:
  - Public endpoints for categories, product catalog, filters, search, product details, catalog download request, and contact/inquiry submissions.
  - Admin endpoints (`/api/v1/admin/*`) for authentication, managing products (Create, Read, Update, Delete), uploading images, managing categories/finishes/sizes.

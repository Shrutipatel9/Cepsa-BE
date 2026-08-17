import os
import re
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session, joinedload
from ..database import get_db
from ..models import Category, Product, ProductImage, Inquiry, User, GalleryItem
from ..schemas import (
    LoginRequest, TokenResponse, DashboardStats, ProductResponse, ProductCreate, ProductUpdate,
    CategoryResponse, CategoryCreate, CategoryUpdate, InquiryResponse, GalleryItemResponse
)
from ..auth import verify_password, create_access_token, get_current_admin
from ..supabase_storage import (
    CATEGORIES_BUCKET,
    PRODUCTS_BUCKET,
    delete_media,
    delete_media_from_gallery_bucket,
    sync_gallery_items_with_supabase,
    upload_file,
    upload_media_to_gallery_bucket,
)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin APIs"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def generate_slug(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug

# Rate Limiting Tracker
FAILED_LOGIN_ATTEMPTS = {}

@router.post("/login", response_model=TokenResponse)
def admin_login(login_data: LoginRequest, db: Session = Depends(get_db)):
    import time
    ip = "client_default"
    
    if ip in FAILED_LOGIN_ATTEMPTS:
        attempts, lock_until = FAILED_LOGIN_ATTEMPTS[ip]
        if time.time() < lock_until:
            remaining_mins = int((lock_until - time.time()) / 60) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Access temporarily locked for {remaining_mins} minute(s)."
            )
        elif time.time() >= lock_until and attempts >= 5:
            FAILED_LOGIN_ATTEMPTS[ip] = (0, 0)

    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        attempts, _ = FAILED_LOGIN_ATTEMPTS.get(ip, (0, 0))
        new_attempts = attempts + 1
        lock_until = time.time() + (15 * 60) if new_attempts >= 5 else 0
        FAILED_LOGIN_ATTEMPTS[ip] = (new_attempts, lock_until)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )
    
    FAILED_LOGIN_ATTEMPTS[ip] = (0, 0)
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "username": user.username}

@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    total_products = db.query(Product).count()
    total_categories = db.query(Category).count()
    total_inquiries = db.query(Inquiry).count()
    featured_products = db.query(Product).filter(Product.is_featured == True).count()

    return {
        "total_products": total_products,
        "total_categories": total_categories,
        "total_inquiries": total_inquiries,
        "featured_products": featured_products
    }

# ================= CATEGORY MANAGEMENT =================

@router.get("/categories", response_model=List[CategoryResponse])
def admin_get_categories(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.id.asc()).all()

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    cat_in: CategoryCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(Category).filter(Category.name.ilike(cat_in.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Category '{cat_in.name}' already exists.")

    slug = generate_slug(cat_in.name)
    category = Category(
        name=cat_in.name,
        slug=slug,
        description=cat_in.description,
        image_url=cat_in.image_url,
        is_active=cat_in.is_active
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    cat_in: CategoryUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = cat_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    if "name" in update_data:
        category.slug = generate_slug(category.name)

    db.commit()
    db.refresh(category)
    return category

@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.image_url:
        delete_media(category.image_url, upload_dir=UPLOAD_DIR)

    db.delete(category)
    db.commit()
    return {"message": f"Category '{category.name}' deleted successfully"}

# ================= PRODUCT MANAGEMENT =================

@router.get("/products", response_model=List[ProductResponse])
def admin_get_products(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    products = db.query(Product).options(
        joinedload(Product.category),
        joinedload(Product.images)
    ).order_by(Product.id.asc()).all()
    return products

@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    slug = generate_slug(f"{product_in.title}-{product_in.product_code}")
    specs_json = json.dumps(product_in.specifications) if product_in.specifications else json.dumps([])
    
    product = Product(
        product_code=product_in.product_code,
        title=product_in.title,
        slug=slug,
        category_id=product_in.category_id,
        specifications=specs_json,
        description=product_in.description,
        is_featured=product_in.is_featured,
        is_new=product_in.is_new,
        is_active=True
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    if product_in.images:
        for idx, img in enumerate(product_in.images):
            prod_img = ProductImage(
                product_id=product.id,
                image_url=img.image_url.split("?")[0],
                is_primary=img.is_primary or (idx == 0),
                display_order=img.display_order or idx
            )
            db.add(prod_img)
        db.commit()
        db.refresh(product)

    return product

@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_in.dict(exclude_unset=True)

    if "images" in update_data:
        images_data = update_data.pop("images")
        if images_data is not None:
            db.query(ProductImage).filter(ProductImage.product_id == product.id).delete()
            for idx, img in enumerate(images_data):
                img_url = img.get("image_url") if isinstance(img, dict) else getattr(img, "image_url", None)
                if img_url:
                    clean_img_url = img_url.split("?")[0]
                    prod_img = ProductImage(
                        product_id=product.id,
                        image_url=clean_img_url,
                        is_primary=img.get("is_primary", idx == 0) if isinstance(img, dict) else (getattr(img, "is_primary", False) or idx == 0),
                        display_order=img.get("display_order", idx) if isinstance(img, dict) else (getattr(img, "display_order", 0) or idx)
                    )
                    db.add(prod_img)

    if "specifications" in update_data and update_data["specifications"] is not None:
        update_data["specifications"] = json.dumps(update_data["specifications"])

    for field, value in update_data.items():
        setattr(product, field, value)

    if "title" in update_data or "product_code" in update_data:
        product.slug = generate_slug(f"{product.title}-{product.product_code}")

    db.commit()
    db.refresh(product)
    return product

@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for img in product.images:
        if img.image_url:
            delete_media(img.image_url, upload_dir=UPLOAD_DIR)

    db.delete(product)
    db.commit()
    return {"message": f"Product '{product.title}' deleted successfully"}

# ================= UPLOAD & INQUIRY APIS =================

@router.post("/upload")
def upload_image(
    file: UploadFile = File(...),
    existing_url: Optional[str] = Form(None),
    kind: Optional[str] = Form("product"),
    current_user: User = Depends(get_current_admin)
):
    try:
        file_bytes = file.file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    bucket = CATEGORIES_BUCKET if (kind or "").strip().lower() == "category" else PRODUCTS_BUCKET

    try:
        public_url, _object_path = upload_file(
            file_bytes=file_bytes,
            filename=file.filename or "image.jpg",
            content_type=file.content_type or "image/jpeg",
            bucket=bucket,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    if existing_url:
        delete_media(existing_url, upload_dir=UPLOAD_DIR)

    return {"image_url": public_url}

@router.get("/inquiries", response_model=List[InquiryResponse])
def get_admin_inquiries(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(Inquiry).order_by(Inquiry.id.desc()).all()

@router.put("/inquiries/{inquiry_id}/status")
def update_inquiry_status(
    inquiry_id: int,
    status_str: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    inquiry.status = status_str
    db.commit()
    return {"message": "Inquiry status updated", "status": status_str}

@router.delete("/inquiries/{inquiry_id}")
def delete_inquiry(
    inquiry_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    db.delete(inquiry)
    db.commit()
    return {"message": f"Inquiry #{inquiry_id} deleted successfully"}

# ================= GALLERY MANAGEMENT =================

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv"}

@router.get("/gallery", response_model=List[GalleryItemResponse])
def admin_get_gallery(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return sync_gallery_items_with_supabase(db)

@router.post("/gallery/upload", response_model=GalleryItemResponse, status_code=status.HTTP_201_CREATED)
def admin_upload_gallery_item(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    display_order: Optional[int] = Form(0),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    filename = file.filename or "file"
    file_ext = os.path.splitext(filename)[1].lower()
    content_type = file.content_type or ""

    is_photo = file_ext in PHOTO_EXTENSIONS or content_type.startswith("image/")
    is_video = file_ext in VIDEO_EXTENSIONS or content_type.startswith("video/")

    if not (is_photo or is_video):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only photo (JPG, PNG, WEBP, GIF, SVG) and video (MP4, WEBM, MOV, AVI) files are allowed."
        )

    item_type = "video" if is_video else "photo"

    try:
        file_bytes = file.file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {str(e)}")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        public_url, storage_filename = upload_media_to_gallery_bucket(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type or ("video/mp4" if item_type == "video" else "image/jpeg")
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Default media title to "Media 1", "Media 2", etc. if no name provided
    if not title or not title.strip():
        existing_count = db.query(GalleryItem).count()
        item_title = f"Media {existing_count + 1}"
    else:
        item_title = title.strip()

    gallery_item = GalleryItem(
        title=item_title,
        item_type=item_type,
        file_url=public_url,
        file_name=storage_filename,
        display_order=display_order or 0
    )
    db.add(gallery_item)
    db.commit()
    db.refresh(gallery_item)
    return gallery_item

@router.delete("/gallery/{item_id}")
def admin_delete_gallery_item(
    item_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")

    # Delete from Supabase Storage 'gallery' bucket
    delete_media_from_gallery_bucket(file_name=item.file_name or "", file_url=item.file_url)

    db.delete(item)
    db.commit()
    return {"message": f"Gallery item #{item_id} deleted successfully"}


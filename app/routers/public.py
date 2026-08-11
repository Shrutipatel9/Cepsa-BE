from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from ..database import get_db
from ..models import Category, Product, Inquiry
from ..schemas import (
    CategoryResponse, ProductResponse, InquiryCreate, InquiryResponse
)

router = APIRouter(prefix="/api/v1/public", tags=["Public APIs"])

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active == True).order_by(Category.id.asc()).all()

@router.get("/products", response_model=List[ProductResponse])
def get_products(
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    is_featured: Optional[bool] = None,
    is_new: Optional[bool] = None,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(Product).options(
        joinedload(Product.category),
        joinedload(Product.images)
    ).filter(Product.is_active == True)

    if category_id:
        query = query.filter(Product.category_id == category_id)
    if is_featured is not None:
        query = query.filter(Product.is_featured == is_featured)
    if is_new is not None:
        query = query.filter(Product.is_new == is_new)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Product.title.ilike(search_term),
                Product.product_code.ilike(search_term),
                Product.specifications.ilike(search_term),
                Product.description.ilike(search_term)
            )
        )

    products = query.order_by(Product.id.desc()).offset(skip).limit(limit).all()
    return products

@router.get("/products/{id_or_slug}", response_model=ProductResponse)
def get_product_detail(id_or_slug: str, db: Session = Depends(get_db)):
    query = db.query(Product).options(
        joinedload(Product.category),
        joinedload(Product.images)
    )

    if id_or_slug.isdigit():
        product = query.filter(Product.id == int(id_or_slug)).first()
    else:
        product = query.filter(Product.slug == id_or_slug).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product

@router.post("/inquiries", response_model=InquiryResponse, status_code=status.HTTP_201_CREATED)
def submit_inquiry(inquiry_in: InquiryCreate, db: Session = Depends(get_db)):
    inq_type = inquiry_in.inquiry_type
    if not inq_type or inq_type == "customer":
        if inquiry_in.product_name or inquiry_in.product_code:
            inq_type = "product"
        else:
            inq_type = "customer"

    inquiry = Inquiry(
        inquiry_type=inq_type,
        customer_name=inquiry_in.customer_name,
        email=inquiry_in.email,
        phone=inquiry_in.phone,
        city=inquiry_in.city,
        product_name=inquiry_in.product_name or inquiry_in.product_code,
        product_code=inquiry_in.product_code,
        message=inquiry_in.message,
        status="Pending"
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    return inquiry

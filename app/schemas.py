import datetime
import json
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

# Category Schemas
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None

class CategoryResponse(CategoryBase):
    id: int
    slug: str

    class Config:
        from_attributes = True

# Image Schemas
class ProductImageBase(BaseModel):
    image_url: str
    is_primary: bool = False
    display_order: int = 0

class ProductImageCreate(ProductImageBase):
    pass

class ProductImageResponse(ProductImageBase):
    id: int
    product_id: int

    class Config:
        from_attributes = True

# Product Schemas
class ProductBase(BaseModel):
    product_code: str
    title: str
    category_id: int
    specifications: Optional[List[str]] = []
    description: Optional[str] = None
    is_featured: bool = False
    is_new: bool = True

class ProductCreate(ProductBase):
    images: Optional[List[ProductImageCreate]] = []

class ProductUpdate(BaseModel):
    product_code: Optional[str] = None
    title: Optional[str] = None
    category_id: Optional[int] = None
    specifications: Optional[List[str]] = None
    description: Optional[str] = None
    is_featured: Optional[bool] = None
    is_new: Optional[bool] = None
    is_active: Optional[bool] = None
    images: Optional[List[ProductImageCreate]] = None

class ProductResponse(BaseModel):
    id: int
    product_code: str
    title: str
    slug: str
    category_id: int
    specifications: List[str] = []
    description: Optional[str] = None
    is_featured: bool
    is_new: bool
    is_active: bool
    created_at: datetime.datetime
    category: CategoryResponse
    images: List[ProductImageResponse] = []

    @field_validator("specifications", mode="before")
    def parse_specifications(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [s.strip() for s in v.split(",") if s.strip()]
        if isinstance(v, list):
            return v
        return []

    class Config:
        from_attributes = True

# Inquiry Schemas
class InquiryCreate(BaseModel):
    inquiry_type: Optional[str] = "customer"
    customer_name: str
    email: str
    phone: str
    city: Optional[str] = None
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    message: Optional[str] = None

class InquiryResponse(InquiryCreate):
    id: int
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Auth Schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

class DashboardStats(BaseModel):
    total_products: int
    total_categories: int
    total_inquiries: int
    featured_products: int

# Gallery Schemas
class GalleryItemBase(BaseModel):
    title: Optional[str] = None
    item_type: str = "photo"  # "photo" or "video"
    display_order: int = 0

class GalleryItemCreate(GalleryItemBase):
    file_url: str
    file_name: Optional[str] = None

class GalleryItemUpdate(BaseModel):
    title: Optional[str] = None
    display_order: Optional[int] = None

class GalleryItemResponse(GalleryItemBase):
    id: int
    file_url: str
    file_name: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class GalleryReorderItem(BaseModel):
    id: int
    display_order: int

class GalleryReorderRequest(BaseModel):
    items: List[GalleryReorderItem]


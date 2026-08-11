import datetime
import json
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from .database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String(50), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    slug = Column(String(180), nullable=False, index=True)
    
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    
    # Stores bullet specifications as JSON array e.g. ["550x360x360 mm", "Rimless Tornado", "P-Trap: 180 mm", "Wall Mount"]
    specifications = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    is_featured = Column(Boolean, default=False)
    is_new = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    category = relationship("Category", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.display_order")


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    image_url = Column(String(500), nullable=False)  # Stores public link from Supabase Storage: categoryid/id
    is_primary = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)

    product = relationship("Product", back_populates="images")


class Inquiry(Base):
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, index=True)
    inquiry_type = Column(String(30), default="customer")  # "customer" or "product"
    customer_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    city = Column(String(100), nullable=True)
    product_name = Column(String(150), nullable=True)
    product_code = Column(String(50), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(30), default="Pending")  # Pending, In Progress, Completed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")
    is_active = Column(Boolean, default=True)

import json
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import Category, Product, ProductImage, User, Inquiry
from .auth import get_password_hash

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Create Default Admin User (cepsaAdminKS)
        admin_user = db.query(User).filter(User.username.in_(["cepsaAdminKS", "admin"])).first()
        if not admin_user:
            admin = User(
                username="cepsaAdminKS",
                email="admin@cepsa.com",
                hashed_password=get_password_hash("Cepsa@Master#2026!Secure"),
                role="admin",
                is_active=True
            )
            db.add(admin)
            print("Created default admin user (cepsaAdminKS / Cepsa@Master#2026!Secure)")
        else:
            admin_user.username = "cepsaAdminKS"
            admin_user.hashed_password = get_password_hash("Cepsa@Master#2026!Secure")
            admin_user.is_active = True

        db.commit()

        # 2. 14 Official Categories ONLY (matching exact user image list)
        categories_data = [
            {
                "name": "ONE PIECE CLOSET",
                "slug": "one-piece-closet",
                "description": "Ergonomic rimless single-structure water closets with dual siphonic flush mechanics.",
                "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "WALL HUNG CLOSET",
                "slug": "wall-hung-closet",
                "description": "Floating wall-mounted water closets engineered with concealed cistern systems for modern space efficiency.",
                "image_url": "https://images.unsplash.com/photo-1620626011761-996317b8d101?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "FLOOR MOUNT",
                "slug": "floor-mount",
                "description": "Heavy-duty floor-mounted water closets designed for maximum stability and easy maintenance.",
                "image_url": "https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "WATER CLOSET",
                "slug": "water-closet",
                "description": "High-grade vitreous china water closets featuring anti-bacterial glaze and powerful flushing.",
                "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "TWO PIECE",
                "slug": "two-piece",
                "description": "Classic two-piece ceramic closets combining separate tank and bowl assemblies with dual flush valves.",
                "image_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "CISTERN AND FITTINGS",
                "slug": "cistern-and-fittings",
                "description": "Precision dual-flush internal cistern fittings, inlet valves, and wall-mounting frame kits.",
                "image_url": "https://images.unsplash.com/photo-1585909692584-35905547783e?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "SEAT COVER",
                "slug": "seat-cover",
                "description": "Soft-close thermoset seat covers with quick-release stainless steel hinges.",
                "image_url": "https://images.unsplash.com/photo-1507652313519-d4e9174996dd?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "FLUSH TANK",
                "slug": "flush-tank",
                "description": "Concealed and exposed dual-flush tanks engineered for low-noise water refills.",
                "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "WASH BASIN",
                "slug": "wash-basin",
                "description": "Architectural ceramic wash basins crafted for elegant bathrooms and powder rooms.",
                "image_url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "ONE PIECE BASIN",
                "slug": "one-piece-basin",
                "description": "Seamless single-structure ceramic wash basins with integrated bowl and overflow protection.",
                "image_url": "https://images.unsplash.com/photo-1604014237800-1c9102c219da?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "WASH BASIN FULL PEDESTAL",
                "slug": "wash-basin-full-pedestal",
                "description": "Floor-standing full pedestal basins concealing plumbing lines with timeless elegance.",
                "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "WASH BASIN HALF PEDESTAL",
                "slug": "wash-basin-half-pedestal",
                "description": "Wall-hung basins with floating half pedestal shrouds for clean floor space.",
                "image_url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "TABLE TOP BASIN",
                "slug": "table-top-basin",
                "description": "Luxury countertop vessel basins with satin-matte, gloss, and metallic artistic glazes.",
                "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=800&q=80"
            },
            {
                "name": "PAN AND URINAL",
                "slug": "pan-and-urinal",
                "description": "High-durability squatting pans and sensor/manual flush urinals for commercial and public fixtures.",
                "image_url": "https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?auto=format&fit=crop&w=800&q=80"
            }
        ]

        valid_slugs = [c["slug"] for c in categories_data]

        # Deactivate any legacy/extra categories not in the official 14 list
        db.query(Category).filter(~Category.slug.in_(valid_slugs)).update({Category.is_active: False}, synchronize_session=False)

        cat_map = {}
        for cat_item in categories_data:
            c = db.query(Category).filter(Category.slug == cat_item["slug"]).first()
            if not c:
                c = Category(**cat_item)
                db.add(c)
                db.flush()
            else:
                c.name = cat_item["name"]
                c.description = cat_item["description"]
                c.image_url = cat_item["image_url"]
                c.is_active = True
                db.flush()
            cat_map[cat_item["slug"]] = c.id

        db.commit()

        # 3. Create Sample Products with Array Specifications matching user image format
        sample_products = [
            # 1. ONE PIECE CLOSET
            {
                "product_code": "LETOP - 1014",
                "title": "LETOP - 1014",
                "slug": "letop-1014",
                "category_slug": "one-piece-closet",
                "specifications": ["660x375x675 mm", "Rimless, 1D Siphonic", "S-Trap: 225, 300 mm"],
                "description": "Rimless 1D Siphonic single piece toilet",
                "is_featured": True,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1000&q=80"]
            },
            {
                "product_code": "AURA - 2040",
                "title": "AURA - 2040",
                "slug": "aura-2040",
                "category_slug": "one-piece-closet",
                "specifications": ["680x380x750 mm", "Dual Siphonic Flush", "Soft-Close UF Seat Cover", "S-Trap: 300 mm"],
                "description": "Dual Siphonic Flush One Piece Closet",
                "is_featured": True,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1000&q=80"]
            },

            # 2. WALL HUNG CLOSET
            {
                "product_code": "CELESTE - 3010",
                "title": "CELESTE - 3010",
                "slug": "celeste-3010",
                "category_slug": "wall-hung-closet",
                "specifications": ["550x360x360 mm", "Rimless Tornado", "P-Trap: 180 mm", "Wall Mount"],
                "description": "Floating Wall Mount Rimless Closet",
                "is_featured": True,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1620626011761-996317b8d101?auto=format&fit=crop&w=1000&q=80"]
            },

            # 3. FLOOR MOUNT
            {
                "product_code": "VERONA - 4005",
                "title": "VERONA - 4005",
                "slug": "verona-4005",
                "category_slug": "floor-mount",
                "specifications": ["660x375x675 mm", "Heavy Duty Floor Mounted", "Anti-Bacterial Glaze", "S-Trap: 220 mm"],
                "description": "Floor Mounted Water Closet",
                "is_featured": False,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?auto=format&fit=crop&w=1000&q=80"]
            },

            # 4. WATER CLOSET
            {
                "product_code": "AQUA - 5012",
                "title": "AQUA - 5012",
                "slug": "aqua-5012",
                "category_slug": "water-closet",
                "specifications": ["660x375x675 mm", "Vitreous China Water Closet", "Eco Dual Flush 3L/4.5L"],
                "description": "Vitreous China Water Closet",
                "is_featured": False,
                "is_new": False,
                "images": ["https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1000&q=80"]
            },

            # 5. TWO PIECE
            {
                "product_code": "ROYAL - 6020",
                "title": "ROYAL - 6020",
                "slug": "royal-6020",
                "category_slug": "two-piece",
                "specifications": ["660x375x675 mm", "Classic Two Piece Structure", "Detachable Ceramic Cistern", "S-Trap: 230 mm"],
                "description": "Two Piece Water Closet",
                "is_featured": False,
                "is_new": False,
                "images": ["https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1000&q=80"]
            },

            # 6. CISTERN AND FITTINGS
            {
                "product_code": "FIT - 7001",
                "title": "FIT - 7001",
                "slug": "fit-7001",
                "category_slug": "cistern-and-fittings",
                "specifications": ["Standard Fit", "Universal Dual-Flush Valve Kit", "High-Pressure Fill Mechanism"],
                "description": "Dual Flush Internal Cistern Fittings",
                "is_featured": False,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1585909692584-35905547783e?auto=format&fit=crop&w=1000&q=80"]
            },

            # 7. SEAT COVER
            {
                "product_code": "SEAT - 8008",
                "title": "SEAT - 8008",
                "slug": "seat-8008",
                "category_slug": "seat-cover",
                "specifications": ["Standard Fit", "Slim UF Soft-Close", "Quick Release Stainless Hinge"],
                "description": "Thermoset UF Soft-Close Seat Cover",
                "is_featured": False,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1507652313519-d4e9174996dd?auto=format&fit=crop&w=1000&q=80"]
            },

            # 8. FLUSH TANK
            {
                "product_code": "TANK - 9002",
                "title": "TANK - 9002",
                "slug": "tank-9002",
                "category_slug": "flush-tank",
                "specifications": ["Standard Fit", "Concealed In-Wall Flush Tank", "Pneumatic Push Button Frame"],
                "description": "Concealed Dual Flush Tank",
                "is_featured": False,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1000&q=80"]
            },

            # 9. WASH BASIN
            {
                "product_code": "BASIN - 1001",
                "title": "BASIN - 1001",
                "slug": "basin-1001",
                "category_slug": "wash-basin",
                "specifications": ["450x350x130 mm", "Wall-Mounted Ceramic Wash Basin", "Faucet Tap Hole & Overflow"],
                "description": "Wall-Mounted Ceramic Wash Basin",
                "is_featured": True,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1000&q=80"]
            },

            # 10. ONE PIECE BASIN
            {
                "product_code": "MONO - 1102",
                "title": "MONO - 1102",
                "slug": "mono-1102",
                "category_slug": "one-piece-basin",
                "specifications": ["560x420x840 mm", "Single Monolithic Ceramic Basin", "Integrated Pedestal Body"],
                "description": "Single Monolithic Wash Basin",
                "is_featured": True,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1604014237800-1c9102c219da?auto=format&fit=crop&w=1000&q=80"]
            },

            # 11. WASH BASIN FULL PEDESTAL
            {
                "product_code": "PED - 1205",
                "title": "PED - 1205",
                "slug": "ped-1205",
                "category_slug": "wash-basin-full-pedestal",
                "specifications": ["560x420x840 mm", "Classic Full Pedestal & Basin Set", "Concealed Drain Lines"],
                "description": "Full Pedestal Basin Set",
                "is_featured": False,
                "is_new": False,
                "images": ["https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1000&q=80"]
            },

            # 12. WASH BASIN HALF PEDESTAL
            {
                "product_code": "HALF - 1308",
                "title": "HALF - 1308",
                "slug": "half-1308",
                "category_slug": "wash-basin-half-pedestal",
                "specifications": ["550x360x360 mm", "Wall Hung Basin", "Floating Half Pedestal Shroud"],
                "description": "Wall Hung Half Pedestal Basin",
                "is_featured": False,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1000&q=80"]
            },

            # 13. TABLE TOP BASIN
            {
                "product_code": "DESIRE - 1410",
                "title": "DESIRE - 1410",
                "slug": "desire-1410",
                "category_slug": "table-top-basin",
                "specifications": ["450x350x130 mm", "Luxury Oval Countertop Vessel Basin", "Ultra-Smooth Ceramic Glaze"],
                "description": "Countertop Vessel Basin",
                "is_featured": True,
                "is_new": True,
                "images": ["https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1000&q=80"]
            },

            # 14. PAN AND URINAL
            {
                "product_code": "PAN - 1502",
                "title": "PAN - 1502",
                "slug": "pan-1502",
                "category_slug": "pan-and-urinal",
                "specifications": ["550x360x360 mm", "Asian Pattern Squatting Pan", "Anti-Slip Treads & Sensor Urinal"],
                "description": "Squatting Pan and Sensor Urinal",
                "is_featured": False,
                "is_new": False,
                "images": ["https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?auto=format&fit=crop&w=1000&q=80"]
            }
        ]

        for p_item in sample_products:
            prod = db.query(Product).filter(Product.product_code == p_item["product_code"]).first()
            cat_id = cat_map.get(p_item["category_slug"])
            specs_str = json.dumps(p_item["specifications"])

            if not prod:
                prod = Product(
                    product_code=p_item["product_code"],
                    title=p_item["title"],
                    slug=p_item["slug"],
                    category_id=cat_id,
                    specifications=specs_str,
                    description=p_item["description"],
                    is_featured=p_item["is_featured"],
                    is_new=p_item["is_new"],
                    is_active=True
                )
                db.add(prod)
                db.flush()

                for idx, img_url in enumerate(p_item["images"]):
                    p_img = ProductImage(
                        product_id=prod.id,
                        image_url=img_url,
                        is_primary=(idx == 0),
                        display_order=idx
                    )
                    db.add(p_img)
            else:
                prod.title = p_item["title"]
                prod.specifications = specs_str
                prod.description = p_item["description"]
                prod.category_id = cat_id
                db.flush()

        db.commit()
        print("Database successfully re-seeded to Supabase PostgreSQL with array specifications.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

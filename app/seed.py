from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import User
from .auth import get_password_hash

def seed_database():
    """Ensure essential admin account exists without injecting dummy products or dummy categories."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Create or verify Default Admin User (cepsaAdminKS)
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
            print("[Seed] Created default admin user (cepsaAdminKS / Cepsa@Master#2026!Secure)")
        else:
            admin_user.username = "cepsaAdminKS"
            admin_user.hashed_password = get_password_hash("Cepsa@Master#2026!Secure")
            admin_user.is_active = True

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Seed Error] {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

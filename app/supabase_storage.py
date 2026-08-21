import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
)
GALLERY_BUCKET = os.getenv("SUPABASE_GALLERY_BUCKET", "gallery")
PRODUCTS_BUCKET = os.getenv("SUPABASE_PRODUCTS_BUCKET", "products")
CATEGORIES_BUCKET = os.getenv("SUPABASE_CATEGORIES_BUCKET", "categories")
ALL_BUCKETS = (PRODUCTS_BUCKET, CATEGORIES_BUCKET, GALLERY_BUCKET)

supabase_client = None
_init_error = ""

try:
    from supabase import create_client
    if SUPABASE_URL and SUPABASE_KEY:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    else:
        _init_error = (
            "Missing SUPABASE_URL or API key. Add SUPABASE_SERVICE_ROLE_KEY "
            "or SUPABASE_ANON_KEY in backend/.env."
        )
except Exception as e:
    _init_error = f"Failed to initialize Supabase client: {e}"
    print(f"[Supabase Init Error] {_init_error}")


def require_client():
    if not supabase_client:
        raise RuntimeError(
            _init_error
            or "Supabase Storage is not configured. Set SUPABASE_URL and a Storage API key in backend/.env."
        )
    return supabase_client


def ensure_storage_infrastructure() -> None:
    """Create public buckets + RLS policies using the Postgres connection."""
    database_url = os.getenv("DATABASE_URL") or ""
    if "postgresql" not in database_url:
        print("[Supabase Storage] DATABASE_URL is not Postgres; skipping bucket bootstrap.")
        return

    from sqlalchemy import create_engine, text

    bucket_sql = """
    INSERT INTO storage.buckets (id, name, public, file_size_limit)
    VALUES (:id, :name, true, 52428800)
    ON CONFLICT (id) DO UPDATE SET public = true, file_size_limit = 52428800
    """
    policy_sql = """
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'cepsa_public_read'
      ) THEN
        CREATE POLICY cepsa_public_read ON storage.objects
        FOR SELECT TO public
        USING (bucket_id IN ('products', 'categories', 'gallery'));
      ELSE
        DROP POLICY cepsa_public_read ON storage.objects;
        CREATE POLICY cepsa_public_read ON storage.objects
        FOR SELECT TO public
        USING (bucket_id IN ('products', 'categories', 'gallery'));
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'cepsa_anon_insert'
      ) THEN
        CREATE POLICY cepsa_anon_insert ON storage.objects
        FOR INSERT TO anon
        WITH CHECK (bucket_id IN ('products', 'categories', 'gallery'));
      ELSE
        DROP POLICY cepsa_anon_insert ON storage.objects;
        CREATE POLICY cepsa_anon_insert ON storage.objects
        FOR INSERT TO anon
        WITH CHECK (bucket_id IN ('products', 'categories', 'gallery'));
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'cepsa_anon_update'
      ) THEN
        CREATE POLICY cepsa_anon_update ON storage.objects
        FOR UPDATE TO anon
        USING (bucket_id IN ('products', 'categories', 'gallery'))
        WITH CHECK (bucket_id IN ('products', 'categories', 'gallery'));
      ELSE
        DROP POLICY cepsa_anon_update ON storage.objects;
        CREATE POLICY cepsa_anon_update ON storage.objects
        FOR UPDATE TO anon
        USING (bucket_id IN ('products', 'categories', 'gallery'))
        WITH CHECK (bucket_id IN ('products', 'categories', 'gallery'));
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'cepsa_anon_delete'
      ) THEN
        CREATE POLICY cepsa_anon_delete ON storage.objects
        FOR DELETE TO anon
        USING (bucket_id IN ('products', 'categories', 'gallery'));
      ELSE
        DROP POLICY cepsa_anon_delete ON storage.objects;
        CREATE POLICY cepsa_anon_delete ON storage.objects
        FOR DELETE TO anon
        USING (bucket_id IN ('products', 'categories', 'gallery'));
      END IF;
    END $$;
    """

    engine = create_engine(database_url)
    try:
        with engine.begin() as conn:
            for bucket in ALL_BUCKETS:
                conn.execute(text(bucket_sql), {"id": bucket, "name": bucket})
            conn.execute(text(policy_sql))
        print("[Supabase Storage] Buckets ready: products, categories, gallery.")
    except Exception as e:
        print(f"[Supabase Storage] Could not bootstrap buckets/policies: {e}")
    finally:
        engine.dispose()


def _guess_content_type(filename: str, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or fallback


def _public_url(bucket: str, object_path: str) -> str:
    client = require_client()
    url = client.storage.from_(bucket).get_public_url(object_path)
    return (url or "").rstrip("?")


def _upload_bytes(bucket: str, object_path: str, file_bytes: bytes, content_type: str) -> str:
    client = require_client()
    options = {"content-type": content_type, "upsert": "true", "x-upsert": "true"}
    try:
        client.storage.from_(bucket).upload(
            path=object_path,
            file=file_bytes,
            file_options=options,
        )
    except Exception as e:
        raise RuntimeError(
            f"Supabase Storage upload failed for {bucket}/{object_path}: {e}. "
            "If this is an RLS / permission error, add SUPABASE_SERVICE_ROLE_KEY "
            "(Project Settings -> API -> service_role) to backend/.env. "
            "Do not put the service role key in the frontend."
        ) from e

    public_url = _public_url(bucket, object_path)
    print(f"[Supabase Storage] Uploaded {bucket}/{object_path}")
    return public_url


def upload_file(
    file_bytes: bytes,
    filename: str,
    content_type: str = "",
    bucket: str = GALLERY_BUCKET,
    object_path: Optional[str] = None,
) -> Tuple[str, str]:
    if not file_bytes:
        raise RuntimeError("Uploaded file is empty.")

    ext = os.path.splitext(filename or "")[1].lower()
    if not ext:
        ext = ".mp4" if (content_type or "").startswith("video/") else ".jpg"
    if not object_path:
        object_path = f"{uuid.uuid4().hex}{ext}"

    content_type = content_type or _guess_content_type(filename or object_path)
    public_url = _upload_bytes(bucket, object_path, file_bytes, content_type)
    return public_url, object_path


def upload_media_to_gallery_bucket(file_bytes: bytes, filename: str, content_type: str) -> Tuple[str, str]:
    return upload_file(
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        bucket=GALLERY_BUCKET,
    )


def parse_storage_ref(url: str) -> Optional[Tuple[str, str]]:
    if not url:
        return None
    clean = url.split("?")[0]
    marker = "/storage/v1/object/public/"
    if marker not in clean:
        return None
    remainder = clean.split(marker, 1)[1]
    bucket, _, object_path = remainder.partition("/")
    if not bucket or not object_path:
        return None
    return bucket, object_path


def is_local_upload_url(url: str) -> bool:
    if not url:
        return False
    clean = url.split("?")[0]
    parsed = urlparse(clean)
    path = parsed.path or clean
    return path.startswith("/uploads/") or "/uploads/" in path


def local_upload_path(url: str, upload_dir: str) -> Optional[str]:
    if not is_local_upload_url(url):
        return None
    clean = url.split("?")[0]
    path = urlparse(clean).path or clean
    relative = path.split("/uploads/", 1)[1]
    return os.path.join(upload_dir, *relative.split("/"))


def delete_from_bucket(bucket: str, object_path: str) -> bool:
    client = require_client()
    try:
        client.storage.from_(bucket).remove([object_path])
        print(f"[Supabase Storage] Deleted {bucket}/{object_path}")
        return True
    except Exception as e:
        print(f"[Supabase Storage] Delete failed for {bucket}/{object_path}: {e}")
        return False


def delete_media(url: str, file_name: str = "", upload_dir: Optional[str] = None) -> bool:
    if file_name and not parse_storage_ref(url or ""):
        try:
            delete_from_bucket(GALLERY_BUCKET, file_name)
        except Exception:
            pass

    ref = parse_storage_ref(url or "")
    if ref:
        bucket, object_path = ref
        try:
            return delete_from_bucket(bucket, object_path)
        except Exception as e:
            print(f"[Supabase Storage] Delete skipped: {e}")
            return False

    if upload_dir:
        local_path = local_upload_path(url or "", upload_dir)
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
                return True
            except Exception as e:
                print(f"[Local Upload] Delete failed for {local_path}: {e}")
    return False


def delete_media_from_gallery_bucket(file_name: str, file_url: str = "") -> bool:
    return delete_media(url=file_url, file_name=file_name)


VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv"}


def list_gallery_filenames() -> Optional[set]:
    """Return object names currently in the gallery bucket, or None if listing fails."""
    try:
        client = require_client()
        files = client.storage.from_(GALLERY_BUCKET).list() or []
    except Exception as e:
        print(f"[Supabase Storage] Could not list gallery bucket: {e}")
        return None

    names = set()
    for item in files:
        name = item.get("name") if isinstance(item, dict) else getattr(item, "name", None)
        if not name or name.endswith("/") or name.startswith(".") or name == ".emptyFolderPlaceholder":
            continue
        names.add(name)
    return names


def is_supabase_gallery_url(url: str) -> bool:
    ref = parse_storage_ref(url or "")
    return bool(ref and ref[0] == GALLERY_BUCKET)


def gallery_object_name(item) -> str:
    if getattr(item, "file_name", None):
        return os.path.basename(item.file_name)
    ref = parse_storage_ref(getattr(item, "file_url", "") or "")
    if ref:
        return os.path.basename(ref[1])
    return ""


def sync_gallery_items_with_supabase(db):
    """
    Keep gallery_items aligned with the gallery bucket:
    - drop local / missing rows
    - create rows for bucket files that are not in the database
    Returns only items that exist in Supabase Storage.
    """
    from .models import GalleryItem

    bucket_names = list_gallery_filenames()
    items = db.query(GalleryItem).all()

    changed = False
    if bucket_names is not None:
        existing_names = set()
        for item in items:
            name = gallery_object_name(item)
            in_bucket = is_supabase_gallery_url(item.file_url or "") and name in bucket_names
            if in_bucket:
                existing_names.add(name)
            else:
                db.delete(item)
                changed = True

        next_index = len(existing_names)
        for name in sorted(bucket_names - existing_names):
            next_index += 1
            ext = os.path.splitext(name)[1].lower()
            item_type = "video" if ext in VIDEO_EXTENSIONS else "photo"
            db.add(GalleryItem(
                title=f"Media {next_index}",
                item_type=item_type,
                file_url=_public_url(GALLERY_BUCKET, name),
                file_name=name,
                display_order=0,
            ))
            changed = True
    else:
        for item in items:
            if not is_supabase_gallery_url(item.file_url or ""):
                db.delete(item)
                changed = True

    if changed:
        db.commit()
        db.expire_all()

    query = db.query(GalleryItem).order_by(GalleryItem.display_order.asc(), GalleryItem.id.asc())
    visible = []
    for item in query.all():
        if not is_supabase_gallery_url(item.file_url or ""):
            continue
        if bucket_names is not None and gallery_object_name(item) not in bucket_names:
            continue
        visible.append(item)
    return visible


def _rewrite_local_url(url: str, public_url: str) -> str:
    if not url:
        return url
    suffix = ""
    if "?" in url:
        suffix = "?" + url.split("?", 1)[1]
    return public_url + suffix


def relocate_category_images() -> int:
    """Move category images that landed in the products bucket into categories."""
    from .database import SessionLocal
    from .models import Category

    client = require_client()
    moved = 0
    db = SessionLocal()
    try:
        for row in db.query(Category).all():
            ref = parse_storage_ref(row.image_url or "")
            if not ref:
                continue
            bucket, object_path = ref
            if bucket == CATEGORIES_BUCKET:
                continue
            try:
                file_bytes = client.storage.from_(bucket).download(object_path)
                public_url = _upload_bytes(
                    CATEGORIES_BUCKET,
                    object_path,
                    file_bytes,
                    _guess_content_type(object_path),
                )
                row.image_url = _rewrite_local_url(row.image_url, public_url)
                delete_from_bucket(bucket, object_path)
                moved += 1
            except Exception as e:
                print(f"[Supabase Storage] Could not move category image {object_path}: {e}")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Supabase Storage] Category relocate failed: {e}")
    finally:
        db.close()
    if moved:
        print(f"[Supabase Storage] Moved {moved} category image(s) into '{CATEGORIES_BUCKET}'.")
    return moved


def migrate_local_files_to_supabase(db, upload_dir: str) -> dict:
    from .models import Category, ProductImage, GalleryItem

    summary = {"uploaded": 0, "updated_rows": 0, "deleted_local": 0, "failed": [], "skipped": 0}

    if not os.path.isdir(upload_dir):
        relocate_category_images()
        return summary

    try:
        require_client()
    except Exception as e:
        summary["failed"].append(str(e))
        print(f"[Supabase Migration] Aborted: {e}")
        return summary

    uploaded_urls = {}

    def migrate_file(abs_path: str, bucket: str, object_path: str) -> Optional[str]:
        rel_key = os.path.relpath(abs_path, upload_dir).replace("\\", "/")
        if rel_key in uploaded_urls:
            return uploaded_urls[rel_key]
        try:
            with open(abs_path, "rb") as handle:
                file_bytes = handle.read()
            if not file_bytes:
                summary["failed"].append(f"{rel_key}: empty file")
                return None
            public_url = _upload_bytes(bucket, object_path, file_bytes, _guess_content_type(abs_path))
            uploaded_urls[rel_key] = public_url
            summary["uploaded"] += 1
            return public_url
        except Exception as e:
            summary["failed"].append(f"{rel_key}: {e}")
            print(f"[Supabase Migration] Failed {rel_key}: {e}")
            return None

    for name in os.listdir(upload_dir):
        abs_path = os.path.join(upload_dir, name)
        if os.path.isfile(abs_path):
            migrate_file(abs_path, PRODUCTS_BUCKET, name)

    gallery_dir = os.path.join(upload_dir, "gallery")
    if os.path.isdir(gallery_dir):
        for name in os.listdir(gallery_dir):
            abs_path = os.path.join(gallery_dir, name)
            if os.path.isfile(abs_path):
                migrate_file(abs_path, GALLERY_BUCKET, name)

    def public_url_for_local(url: str, bucket: str) -> Optional[str]:
        local_path = local_upload_path(url, upload_dir)
        if not local_path:
            return None
        rel_key = os.path.relpath(local_path, upload_dir).replace("\\", "/")
        if rel_key in uploaded_urls:
            return uploaded_urls[rel_key]
        if not os.path.exists(local_path):
            return None
        return migrate_file(local_path, bucket, os.path.basename(local_path))

    for row in db.query(Category).all():
        if is_local_upload_url(row.image_url or ""):
            public_url = public_url_for_local(row.image_url, CATEGORIES_BUCKET)
            if public_url:
                row.image_url = _rewrite_local_url(row.image_url, public_url)
                summary["updated_rows"] += 1

    for row in db.query(ProductImage).all():
        if is_local_upload_url(row.image_url or ""):
            public_url = public_url_for_local(row.image_url, PRODUCTS_BUCKET)
            if public_url:
                row.image_url = _rewrite_local_url(row.image_url, public_url)
                summary["updated_rows"] += 1

    for row in db.query(GalleryItem).all():
        if is_local_upload_url(row.file_url or ""):
            public_url = public_url_for_local(row.file_url, GALLERY_BUCKET)
            if public_url:
                row.file_url = _rewrite_local_url(row.file_url, public_url)
                if not row.file_name:
                    row.file_name = os.path.basename(public_url.split("?")[0])
                summary["updated_rows"] += 1

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        summary["failed"].append(f"database commit: {e}")
        print(f"[Supabase Migration] DB commit failed: {e}")
        return summary

    for rel_key in list(uploaded_urls.keys()):
        abs_path = os.path.join(upload_dir, *rel_key.split("/"))
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
                summary["deleted_local"] += 1
        except Exception as e:
            summary["failed"].append(f"delete {rel_key}: {e}")

    relocate_category_images()
    print(
        f"[Supabase Migration] uploaded={summary['uploaded']} "
        f"updated_rows={summary['updated_rows']} deleted_local={summary['deleted_local']} "
        f"failed={len(summary['failed'])}"
    )
    return summary

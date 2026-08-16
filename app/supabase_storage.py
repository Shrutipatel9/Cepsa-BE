import os
import uuid
import requests
from typing import Tuple, Optional

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wcysphccjnvzygwtknbw.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GALLERY_BUCKET = os.getenv("SUPABASE_GALLERY_BUCKET", "gallery")

# Local upload directory fallback
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "gallery")
os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)


def upload_media_to_gallery_bucket(file_bytes: bytes, filename: str, content_type: str) -> Tuple[str, str]:
    """
    Uploads photo/video to Supabase Storage 'gallery' bucket.
    Returns (public_url, storage_file_name).
    If Supabase key/bucket API fails or is offline, falls back to local storage seamlessly.
    """
    ext = os.path.splitext(filename)[1].lower()
    if not ext:
        ext = ".mp4" if "video" in content_type else ".jpg"

    unique_name = f"{uuid.uuid4().hex}{ext}"
    bucket_path = f"{unique_name}"

    # Try uploading to Supabase Storage API
    try:
        upload_endpoint = f"{SUPABASE_URL}/storage/v1/object/{GALLERY_BUCKET}/{bucket_path}"
        headers = {
            "Content-Type": content_type,
            "x-upsert": "true"
        }
        if SUPABASE_KEY:
            headers["Authorization"] = f"Bearer {SUPABASE_KEY}"

        response = requests.post(upload_endpoint, data=file_bytes, headers=headers, timeout=12)
        
        if response.status_code in (200, 201):
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{GALLERY_BUCKET}/{bucket_path}"
            return public_url, bucket_path
        else:
            print(f"[Supabase Storage] Notice ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"[Supabase Storage Error] {e}")

    # Fallback: Save to local uploads/gallery
    local_path = os.path.join(LOCAL_UPLOAD_DIR, unique_name)
    with open(local_path, "wb") as f:
        f.write(file_bytes)

    public_url = f"/uploads/gallery/{unique_name}"
    return public_url, unique_name


def delete_media_from_gallery_bucket(file_name: str, file_url: str = "") -> bool:
    """
    Deletes photo/video from Supabase Storage 'gallery' bucket or local fallback.
    """
    if not file_name and file_url:
        file_name = os.path.basename(file_url.split("?")[0])

    if not file_name:
        return False

    # Try deleting from Supabase
    try:
        delete_endpoint = f"{SUPABASE_URL}/storage/v1/object/{GALLERY_BUCKET}/{file_name}"
        headers = {}
        if SUPABASE_KEY:
            headers["Authorization"] = f"Bearer {SUPABASE_KEY}"

        response = requests.delete(delete_endpoint, headers=headers, timeout=8)
        if response.status_code in (200, 204):
            print(f"[Supabase Storage] Deleted {file_name} from '{GALLERY_BUCKET}'")
    except Exception as e:
        print(f"[Supabase Storage Delete Error] {e}")

    # Also clean up local fallback file if exists
    local_path = os.path.join(LOCAL_UPLOAD_DIR, file_name)
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
            print(f"[Local Storage] Deleted local fallback file {file_name}")
        except Exception as e:
            print(f"[Local Delete Error] {e}")

    return True

#!/usr/bin/env python3
"""Final cleanup: consolidate all files to uploads/ with correct names."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.database.client import get_client
import requests

def list_files(prefix):
    """List files using direct API."""
    url = f"{settings.SUPABASE_URL}/storage/v1/object/list/{settings.SUPABASE_BUCKET}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    }

    payload = {
        "limit": 1000,
        "offset": 0,
        "prefix": prefix,
        "sortBy": {"column": "name", "order": "asc"}
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return [f['name'] for f in response.json() if f.get('id')]
    return []

def delete_file(path):
    """Delete a file from storage."""
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_BUCKET}/{path}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    }

    response = requests.delete(url, headers=headers)
    return response.status_code in [200, 204]

def download_file(path):
    """Download file from storage."""
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_BUCKET}/{path}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    return None

def upload_file(path, content):
    """Upload file to storage."""
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_BUCKET}/{path}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/pdf"
    }

    response = requests.post(url, data=content, headers=headers)
    return response.status_code in [200, 201]

def cleanup():
    """Main cleanup logic."""
    print("="*60)
    print("FINAL STORAGE CLEANUP")
    print("="*60)

    # Get database samples
    client = get_client()
    result = client.table("dataset_samples").select("id, filename").execute()
    db_samples = {s['filename']: s['id'] for s in result.data}

    print(f"\n📋 Database: {len(db_samples)} samples")

    # List current files
    uploads_files = list_files('uploads')
    samples_files = list_files('samples')

    print(f"\n📦 Current storage:")
    print(f"   uploads/: {len(uploads_files)} files")
    print(f"   samples/: {len(samples_files)} files")

    # Strategy:
    # 1. Copy all files from samples/ to uploads/ with real names
    # 2. Delete all old files in uploads/
    # 3. Delete all files in samples/
    # 4. Update database paths to uploads/filename

    print(f"\n🔄 Step 1: Copying files from samples/ to uploads/...")

    copied = 0
    for file_path in samples_files:
        filename = file_path.split('/')[-1]

        if filename not in db_samples:
            print(f"   ⚠️  Skipping {filename} (not in database)")
            continue

        # Download from samples/
        content = download_file(file_path)
        if not content:
            print(f"   ✗ Failed to download {file_path}")
            continue

        # Upload to uploads/ with real name
        new_path = f"uploads/{filename}"
        if upload_file(new_path, content):
            print(f"   ✓ Copied: {filename}")
            copied += 1
        else:
            print(f"   ✗ Failed to upload {new_path}")

    print(f"\n✅ Copied {copied} files from samples/ to uploads/")

    # Check if all DB samples now have files in uploads/
    print(f"\n🔍 Verifying all samples have files...")

    missing = []
    uploads_with_real_names = list_files('uploads')

    for filename in db_samples.keys():
        expected_path = f"uploads/{filename}"
        if expected_path not in uploads_with_real_names:
            missing.append(filename)

    if missing:
        print(f"   ⚠️  Missing {len(missing)} files:")
        for f in missing[:5]:
            print(f"      - {f}")

    # Now delete ALL old files
    print(f"\n🗑️  Step 2: Deleting old files...")

    # Get all uploads files again
    all_uploads = list_files('uploads')

    # Keep only files with real names (matching DB)
    to_keep = [f"uploads/{filename}" for filename in db_samples.keys()]
    to_delete_uploads = [f for f in all_uploads if f not in to_keep]

    print(f"   Files to delete from uploads/: {len(to_delete_uploads)}")

    deleted_uploads = 0
    for path in to_delete_uploads:
        if delete_file(path):
            deleted_uploads += 1
            if deleted_uploads % 10 == 0:
                print(f"      Deleted {deleted_uploads}/{len(to_delete_uploads)}...")

    print(f"   ✅ Deleted {deleted_uploads} old files from uploads/")

    # Delete all files from samples/
    print(f"\n🗑️  Step 3: Deleting samples/ folder...")

    deleted_samples = 0
    for path in samples_files:
        if delete_file(path):
            deleted_samples += 1

    print(f"   ✅ Deleted {deleted_samples} files from samples/")

    # Update database paths
    print(f"\n🔄 Step 4: Updating database paths...")

    updated = 0
    for filename, sample_id in db_samples.items():
        correct_path = f"uploads/{filename}"

        try:
            client.table("dataset_samples").update({
                "pdf_storage_path": correct_path
            }).eq("id", sample_id).execute()
            updated += 1
        except Exception as e:
            print(f"   ⚠️  Failed to update {filename}: {e}")

    print(f"   ✅ Updated {updated} database paths")

    # Final verification
    print(f"\n{'='*60}")
    print(f"✅ CLEANUP COMPLETE")
    print(f"{'='*60}")

    final_uploads = list_files('uploads')
    final_samples = list_files('samples')

    print(f"\n📦 Final storage state:")
    print(f"   uploads/: {len(final_uploads)} files")
    print(f"   samples/: {len(final_samples)} files")

    print(f"\n📋 Database samples: {len(db_samples)}")

    if len(final_uploads) == len(db_samples):
        print(f"\n✅ Perfect! {len(final_uploads)} files = {len(db_samples)} database records")
    else:
        print(f"\n⚠️  Mismatch: {len(final_uploads)} files vs {len(db_samples)} database records")

if __name__ == "__main__":
    cleanup()

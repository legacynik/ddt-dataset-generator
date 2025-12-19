#!/usr/bin/env python3
"""Simple cleanup: delete files not referenced by database."""

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

def simple_cleanup():
    """Delete only files NOT referenced by database."""
    print("="*60)
    print("SIMPLE CLEANUP: Remove unreferenced files")
    print("="*60)

    # Get all database paths
    client = get_client()
    result = client.table("dataset_samples").select("pdf_storage_path").execute()
    db_paths = set(s['pdf_storage_path'] for s in result.data if s['pdf_storage_path'])

    print(f"\n📋 Database references {len(db_paths)} files:")
    for path in sorted(list(db_paths))[:5]:
        print(f"   - {path}")
    if len(db_paths) > 5:
        print(f"   ... and {len(db_paths) - 5} more")

    # Get all storage files (list_files returns names like "filename.pdf", not "uploads/filename.pdf")
    uploads_files_raw = list_files('uploads')
    samples_files_raw = list_files('samples')

    # Add back the folder prefix for comparison
    uploads_files = set(f"uploads/{f}" if not f.startswith('uploads/') else f for f in uploads_files_raw)
    samples_files = set(f"samples/{f}" if not f.startswith('samples/') else f for f in samples_files_raw)

    all_files = uploads_files | samples_files

    print(f"\n📦 Storage has {len(all_files)} files total:")
    print(f"   - uploads/: {len(uploads_files)}")
    print(f"   - samples/: {len(samples_files)}")

    # Find files to delete (not in DB)
    to_delete = all_files - db_paths

    print(f"\n🗑️  Files to DELETE ({len(to_delete)} unreferenced):")
    for path in sorted(list(to_delete))[:10]:
        print(f"   - {path}")
    if len(to_delete) > 10:
        print(f"   ... and {len(to_delete) - 10} more")

    # Find files in DB but missing from storage
    missing = db_paths - all_files

    if missing:
        print(f"\n⚠️  Files referenced by DB but MISSING from storage ({len(missing)}):")
        for path in sorted(list(missing))[:5]:
            print(f"   - {path}")

    if not to_delete:
        print(f"\n✅ No unreferenced files to delete!")
        return

    print(f"\n🗑️  Deleting {len(to_delete)} unreferenced files...")

    deleted = 0
    failed = 0

    for path in to_delete:
        try:
            if delete_file(path):
                deleted += 1
                if deleted % 10 == 0:
                    print(f"   Deleted {deleted}/{len(to_delete)}...")
            else:
                failed += 1
        except Exception as e:
            print(f"   ⚠️  Failed: {path} - {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"✅ CLEANUP COMPLETE")
    print(f"   Deleted: {deleted}")
    print(f"   Failed: {failed}")
    print(f"{'='*60}")

    # Final count
    final_uploads = list_files('uploads')
    final_samples = list_files('samples')

    print(f"\n📦 Final storage:")
    print(f"   uploads/: {len(final_uploads)} files")
    print(f"   samples/: {len(final_samples)} files")
    print(f"   TOTAL: {len(final_uploads) + len(final_samples)} files")

    print(f"\n📋 Database references: {len(db_paths)} files")

    if len(final_uploads) + len(final_samples) == len(db_paths):
        print(f"\n✅ Perfect match! Storage = Database")
    else:
        diff = (len(final_uploads) + len(final_samples)) - len(db_paths)
        if diff > 0:
            print(f"\n⚠️  Still {diff} extra files in storage")
        else:
            print(f"\n⚠️  Missing {-diff} files referenced by database")

if __name__ == "__main__":
    simple_cleanup()

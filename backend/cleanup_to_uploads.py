#!/usr/bin/env python3
"""Clean up Supabase Storage - consolidate everything in uploads/ folder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database.client import get_storage, get_client

def list_storage():
    """List all files in storage."""
    storage = get_storage()

    try:
        result = storage.list()

        by_folder = {}
        by_filename = {}  # Track duplicates by actual filename

        for item in result:
            path = item.get('name', '')
            if '/' in path:
                folder, filename = path.rsplit('/', 1)
                by_folder.setdefault(folder, []).append(path)
                by_filename.setdefault(filename, []).append(path)

        return by_folder, by_filename
    except Exception as e:
        print(f"Error listing storage: {e}")
        return {}, {}

def cleanup():
    """Consolidate to uploads/ folder only."""
    storage = get_storage()
    client = get_client()

    print("="*60)
    print("CONSOLIDATING TO uploads/ FOLDER")
    print("="*60)

    by_folder, by_filename = list_storage()

    print(f"\nCurrent structure:")
    for folder, files in sorted(by_folder.items()):
        print(f"  📁 {folder}/ → {len(files)} files")

    # Get all database samples
    db_result = client.table("dataset_samples").select("id, filename, pdf_storage_path").execute()
    db_samples = {s['filename']: s for s in db_result.data}

    print(f"\n📋 Database: {len(db_samples)} samples")

    # Track which files to keep in uploads/
    uploads_files = by_folder.get('uploads', [])
    samples_files = by_folder.get('samples', [])

    print(f"\n📊 Analysis:")
    print(f"  - Files in uploads/: {len(uploads_files)}")
    print(f"  - Files in samples/: {len(samples_files)}")

    # Map filenames to their uploads/ paths
    uploads_map = {}
    for path in uploads_files:
        filename = path.split('/')[-1].split('.')[0]  # Get UUID
        # Find actual filename from database
        for db_filename, db_sample in db_samples.items():
            if db_sample['pdf_storage_path'] == path:
                uploads_map[db_filename] = path
                break

    # Map samples/ files to filenames
    samples_map = {}
    for path in samples_files:
        filename = path.split('/')[-1]  # Get actual filename like "doc01...pdf"
        samples_map[filename] = path

    print(f"\n🔄 Processing...")

    # For each DB sample, ensure it has a file in uploads/
    moved = 0
    deleted = 0
    updated_paths = 0

    for db_filename, db_sample in db_samples.items():
        current_path = db_sample['pdf_storage_path']

        # Check if file is in uploads/
        if current_path and current_path.startswith('uploads/'):
            # Already in uploads/, just verify
            print(f"  ✓ {db_filename} - already in uploads/")
            continue

        # Check if file is in samples/
        if current_path and current_path.startswith('samples/'):
            # Need to move from samples/ to uploads/
            # But we need to check if it already exists in uploads/

            # Generate new uploads/ path
            new_path = f"uploads/{db_filename}"

            try:
                # Check if already exists in uploads/
                existing_in_uploads = any(p.endswith(db_filename) for p in uploads_files)

                if existing_in_uploads:
                    # File already exists in uploads/, just update DB
                    print(f"  ⚙️  {db_filename} - file exists in uploads/, updating DB")
                    # Find the exact path
                    upload_path = next(p for p in uploads_files if p.endswith(db_filename))
                    client.table("dataset_samples").update({
                        "pdf_storage_path": upload_path
                    }).eq("id", db_sample["id"]).execute()
                    updated_paths += 1
                else:
                    # Copy from samples/ to uploads/
                    print(f"  📦 {db_filename} - copying from samples/ to uploads/")

                    # Download from samples/
                    file_data = storage.download(current_path)

                    # Upload to uploads/
                    storage.upload(new_path, file_data, {"content-type": "application/pdf"})

                    # Update DB
                    client.table("dataset_samples").update({
                        "pdf_storage_path": new_path
                    }).eq("id", db_sample["id"]).execute()

                    moved += 1

            except Exception as e:
                print(f"  ⚠️  {db_filename} - error: {e}")

    print(f"\n🗑️  Cleaning up samples/ folder...")

    # Delete all files in samples/
    for path in samples_files:
        try:
            storage.remove([path])
            print(f"  ✗ Deleted: {path}")
            deleted += 1
        except Exception as e:
            print(f"  ⚠️  Failed to delete {path}: {e}")

    # Remove duplicate uploads if any
    print(f"\n🔍 Checking for duplicates in uploads/...")

    # Group uploads by actual filename (from DB)
    uploads_by_dbname = {}
    for db_filename, db_sample in db_samples.items():
        path = db_sample['pdf_storage_path']
        if path and path.startswith('uploads/'):
            uploads_by_dbname.setdefault(db_filename, []).append((db_sample['id'], path))

    # Find duplicates
    for db_filename, items in uploads_by_dbname.items():
        if len(items) > 1:
            print(f"  ⚠️  Duplicate: {db_filename} has {len(items)} entries")
            # Keep the first one, delete others
            keep_id, keep_path = items[0]
            for dup_id, dup_path in items[1:]:
                if dup_path != keep_path:
                    try:
                        storage.remove([dup_path])
                        print(f"    ✗ Deleted duplicate: {dup_path}")
                    except:
                        pass

    print(f"\n{'='*60}")
    print(f"✅ CLEANUP COMPLETE")
    print(f"   - {moved} files moved from samples/ to uploads/")
    print(f"   - {deleted} files deleted from samples/")
    print(f"   - {updated_paths} database paths updated")
    print(f"{'='*60}")

    # Show final state
    by_folder, _ = list_storage()
    print(f"\n📁 Final structure:")
    for folder, files in sorted(by_folder.items()):
        print(f"  {folder}/ → {len(files)} files")

if __name__ == "__main__":
    cleanup()

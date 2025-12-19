#!/usr/bin/env python3
"""Remove duplicate files from Supabase Storage using filename as unique key."""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from src.database.client import get_client, get_storage

def get_all_storage_files():
    """Get all files from uploads/ folder."""
    storage = get_storage()

    try:
        # List all files
        result = storage.list()

        uploads_files = []
        for item in result:
            path = item.get('name', '')
            if path.startswith('uploads/'):
                uploads_files.append(path)

        return uploads_files
    except Exception as e:
        print(f"Error listing files: {e}")
        return []

def get_db_samples():
    """Get all samples from database."""
    client = get_client()

    result = client.table("dataset_samples").select("id, filename, pdf_storage_path").execute()
    return {s['filename']: s for s in result.data}

def extract_real_filename(storage_path):
    """Extract real filename from storage path.

    Examples:
        uploads/doc01128620251217151633_001.pdf -> doc01128620251217151633_001.pdf
        uploads/uuid.pdf -> uuid.pdf (but we'll match by database)
    """
    return storage_path.split('/')[-1]

def remove_duplicates():
    """Remove duplicate files, keeping only one per unique filename."""
    storage = get_storage()

    print("="*60)
    print("REMOVING DUPLICATES FROM SUPABASE STORAGE")
    print("="*60)

    # Get all files
    all_files = get_all_storage_files()
    print(f"\n📦 Found {len(all_files)} files in uploads/\n")

    # Get database samples
    db_samples = get_db_samples()
    print(f"📋 Found {len(db_samples)} samples in database\n")

    # Group files by real filename
    by_real_filename = defaultdict(list)

    for storage_path in all_files:
        # Extract the actual filename
        path_parts = storage_path.split('/')
        file_part = path_parts[-1]  # e.g., "uuid.pdf" or "doc01...pdf"

        # Try to match with database samples
        matched_filename = None

        # Check if this file_part is a direct match with any DB filename
        if file_part in db_samples:
            matched_filename = file_part
        else:
            # Check if any DB sample points to this path
            for db_filename, db_sample in db_samples.items():
                if db_sample['pdf_storage_path'] == storage_path:
                    matched_filename = db_filename
                    break

        if matched_filename:
            by_real_filename[matched_filename].append(storage_path)
        else:
            # Orphan file (not in database)
            by_real_filename[f"_ORPHAN_{file_part}"].append(storage_path)

    print(f"📊 Analysis:")
    print(f"   Unique filenames: {len(by_real_filename)}")

    # Find duplicates and orphans
    duplicates = {k: v for k, v in by_real_filename.items() if len(v) > 1}
    orphans = {k: v for k, v in by_real_filename.items() if k.startswith('_ORPHAN_')}

    print(f"   Files with duplicates: {len(duplicates)}")
    print(f"   Orphan files: {len(orphans)}")

    # Show duplicates
    if duplicates:
        print(f"\n⚠️  DUPLICATES FOUND:")
        for filename, paths in sorted(duplicates.items())[:10]:
            print(f"\n   {filename} → {len(paths)} copies:")
            for path in paths:
                print(f"     - {path}")
        if len(duplicates) > 10:
            print(f"\n   ... and {len(duplicates) - 10} more")

    # Show orphans
    if orphans:
        print(f"\n🗑️  ORPHAN FILES (not in database):")
        for key, paths in sorted(orphans.items())[:10]:
            for path in paths:
                print(f"     - {path}")
        if len(orphans) > 10:
            total_orphan_files = sum(len(paths) for paths in orphans.values())
            print(f"   ... and {total_orphan_files - 10} more")

    # Calculate what to delete
    to_delete = []
    to_keep = {}

    for filename, paths in by_real_filename.items():
        if len(paths) == 1:
            # No duplicates, keep it
            to_keep[filename] = paths[0]
        else:
            # Multiple copies - keep one, delete others
            if filename.startswith('_ORPHAN_'):
                # Orphan - delete all
                to_delete.extend(paths)
            else:
                # Check which one the DB points to
                db_sample = db_samples.get(filename)
                if db_sample and db_sample['pdf_storage_path'] in paths:
                    # Keep the one DB points to
                    keep_path = db_sample['pdf_storage_path']
                    to_keep[filename] = keep_path
                    to_delete.extend([p for p in paths if p != keep_path])
                else:
                    # Keep first one, delete others
                    to_keep[filename] = paths[0]
                    to_delete.extend(paths[1:])

    print(f"\n📋 PLAN:")
    print(f"   Files to keep: {len(to_keep)}")
    print(f"   Files to delete: {len(to_delete)}")

    if not to_delete:
        print("\n✅ No duplicates to remove! Storage is clean.")
        return

    print(f"\n⚠️  This will DELETE {len(to_delete)} files from Supabase Storage!")
    print("\nFiles to delete:")
    for path in sorted(to_delete)[:20]:
        print(f"  ✗ {path}")
    if len(to_delete) > 20:
        print(f"  ... and {len(to_delete) - 20} more")

    # Auto-proceed with deletion
    print(f"\n🗑️  Deleting {len(to_delete)} duplicate/orphan files...")

    deleted = 0
    failed = 0

    for path in to_delete:
        try:
            storage.remove([path])
            deleted += 1
            if deleted % 10 == 0:
                print(f"   Deleted {deleted}/{len(to_delete)}...")
        except Exception as e:
            print(f"   ⚠️  Failed to delete {path}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"✅ CLEANUP COMPLETE")
    print(f"   Deleted: {deleted} files")
    print(f"   Failed: {failed} files")
    print(f"   Remaining: {len(to_keep)} unique files")
    print(f"{'='*60}")

    # Verify DB paths
    print(f"\n🔍 Verifying database paths...")

    client = get_client()
    fixed = 0

    for filename, kept_path in to_keep.items():
        if filename.startswith('_ORPHAN_'):
            continue

        db_sample = db_samples.get(filename)
        if not db_sample:
            continue

        if db_sample['pdf_storage_path'] != kept_path:
            # Update DB to point to kept file
            try:
                client.table("dataset_samples").update({
                    "pdf_storage_path": kept_path
                }).eq("id", db_sample["id"]).execute()
                print(f"   ✓ Fixed DB path for {filename}")
                fixed += 1
            except Exception as e:
                print(f"   ⚠️  Failed to fix {filename}: {e}")

    if fixed > 0:
        print(f"\n✅ Fixed {fixed} database paths")
    else:
        print(f"\n✅ All database paths are correct")

    # Show final count
    final_files = get_all_storage_files()
    print(f"\n📦 Final count: {len(final_files)} files in uploads/")

if __name__ == "__main__":
    remove_duplicates()

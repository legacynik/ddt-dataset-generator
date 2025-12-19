#!/usr/bin/env python3
"""Final cleanup: ensure all DB paths point to uploads/ and verify storage."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database.client import get_client, get_storage

def update_all_paths_to_uploads():
    """Update all database paths to use uploads/ folder."""
    client = get_client()

    # Get all samples
    result = client.table("dataset_samples").select("id, filename, pdf_storage_path").execute()
    samples = result.data

    print(f"📋 Found {len(samples)} samples in database\n")

    updated = 0
    for sample in samples:
        current_path = sample['pdf_storage_path']
        filename = sample['filename']

        # Determine correct path
        if current_path and current_path.startswith('uploads/'):
            # Already correct
            print(f"  ✓ {filename} - already in uploads/")
            continue

        # Generate new path
        new_path = f"uploads/{filename}"

        try:
            client.table("dataset_samples").update({
                "pdf_storage_path": new_path
            }).eq("id", sample["id"]).execute()

            print(f"  🔄 {filename}: {current_path} → {new_path}")
            updated += 1
        except Exception as e:
            print(f"  ⚠️  {filename}: error - {e}")

    print(f"\n{'='*60}")
    print(f"✅ Updated {updated} paths to uploads/")
    print(f"{'='*60}")

def verify_storage():
    """Verify storage state."""
    storage = get_storage()

    print(f"\n📦 Verifying Supabase Storage...\n")

    try:
        # List files
        result = storage.list()

        by_folder = {}
        for item in result:
            path = item.get('name', '')
            if '/' in path:
                folder = path.split('/')[0]
                by_folder.setdefault(folder, []).append(path)

        print("Current folders:")
        for folder, files in sorted(by_folder.items()):
            print(f"  📁 {folder}/ → {len(files)} files")
            for f in sorted(files)[:3]:
                print(f"     - {f.split('/')[-1]}")
            if len(files) > 3:
                print(f"     ... and {len(files) - 3} more")

    except Exception as e:
        print(f"  ⚠️  Error: {e}")

def main():
    print("="*60)
    print("FINAL CLEANUP: CONSOLIDATE TO uploads/")
    print("="*60)

    # Update all database paths
    update_all_paths_to_uploads()

    # Verify storage
    verify_storage()

    print(f"\n✅ Cleanup complete! All samples now use uploads/ folder.")

if __name__ == "__main__":
    main()

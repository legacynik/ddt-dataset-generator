#!/usr/bin/env python3
"""Clean up Supabase Storage - keep only samples/ folder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database.client import get_storage, get_client

def list_all_files():
    """List all files in storage bucket."""
    storage = get_storage()

    print("Fetching all files from Supabase Storage...\n")

    try:
        # List all files
        result = storage.list()

        if not result:
            print("No files found in storage")
            return []

        files_by_folder = {}
        for item in result:
            name = item.get('name', '')
            if '/' in name:
                folder = name.split('/')[0]
                files_by_folder.setdefault(folder, []).append(name)
            else:
                files_by_folder.setdefault('root', []).append(name)

        print("Current storage structure:")
        print("="*60)
        for folder, files in sorted(files_by_folder.items()):
            print(f"\n📁 {folder}/ ({len(files)} files)")
            for f in sorted(files)[:5]:  # Show first 5
                print(f"   - {f}")
            if len(files) > 5:
                print(f"   ... and {len(files) - 5} more")

        print("\n" + "="*60)
        return result

    except Exception as e:
        print(f"Error listing files: {e}")
        return []

def cleanup_storage():
    """Remove all files not in samples/ folder."""
    storage = get_storage()

    files = list_all_files()
    if not files:
        return

    # Separate samples/ files from others
    samples_files = []
    other_files = []

    for item in files:
        name = item.get('name', '')
        if name.startswith('samples/'):
            samples_files.append(name)
        else:
            other_files.append(name)

    print(f"\n📊 Summary:")
    print(f"   ✓ Files in samples/: {len(samples_files)}")
    print(f"   ✗ Files elsewhere: {len(other_files)}")

    if not other_files:
        print("\n✓ Storage is already clean! Only samples/ folder exists.")
        return

    print(f"\n⚠️  Found {len(other_files)} files outside samples/ folder:")
    for f in other_files[:10]:
        print(f"   - {f}")
    if len(other_files) > 10:
        print(f"   ... and {len(other_files) - 10} more")

    response = input("\nDelete these files? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return

    # Delete files not in samples/
    deleted = 0
    for file_path in other_files:
        try:
            storage.remove([file_path])
            print(f"✗ Deleted: {file_path}")
            deleted += 1
        except Exception as e:
            print(f"⚠ Failed to delete {file_path}: {e}")

    print(f"\n{'='*60}")
    print(f"Cleanup complete: {deleted} files deleted")
    print(f"{'='*60}")

def verify_database_paths():
    """Verify all database paths point to samples/."""
    client = get_client()

    result = client.table("dataset_samples").select("id, filename, pdf_storage_path").execute()
    samples = result.data

    print(f"\n📋 Verifying database paths ({len(samples)} samples)...\n")

    wrong_paths = []
    for sample in samples:
        path = sample.get('pdf_storage_path')
        if path and not path.startswith('samples/'):
            wrong_paths.append(sample)

    if wrong_paths:
        print(f"⚠️  Found {len(wrong_paths)} samples with wrong paths:")
        for s in wrong_paths[:5]:
            print(f"   - {s['filename']}: {s['pdf_storage_path']}")
        if len(wrong_paths) > 5:
            print(f"   ... and {len(wrong_paths) - 5} more")

        response = input("\nFix these paths to samples/? (yes/no): ")
        if response.lower() == 'yes':
            for sample in wrong_paths:
                filename = sample['filename']
                new_path = f"samples/{filename}"
                client.table("dataset_samples").update({
                    "pdf_storage_path": new_path
                }).eq("id", sample["id"]).execute()
                print(f"✓ Fixed: {filename} → {new_path}")
    else:
        print("✓ All database paths correctly point to samples/")

def main():
    """Main entry point."""
    print("="*60)
    print("SUPABASE STORAGE CLEANUP")
    print("="*60)

    # Verify database paths first
    verify_database_paths()

    # Clean up storage
    print()
    cleanup_storage()

    # Show final state
    print("\n\n" + "="*60)
    print("FINAL STATE")
    print("="*60)
    list_all_files()

if __name__ == "__main__":
    main()

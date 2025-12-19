#!/usr/bin/env python3
"""Clean up duplicate samples in database and move files to 'uploaded' folder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database import SampleRepository, SampleStatus
from src.database.client import get_client

def cleanup_duplicates():
    """Remove duplicate samples, keeping only processed ones."""
    repo = SampleRepository()
    client = get_client()

    # Get all samples
    samples = repo.get_samples(limit=1000)

    # Group by filename
    by_filename = {}
    for sample in samples:
        by_filename.setdefault(sample.filename, []).append(sample)

    print(f"Total samples: {len(samples)}")
    print(f"Unique filenames: {len(by_filename)}\n")

    deleted_count = 0
    updated_count = 0

    for filename, sample_list in sorted(by_filename.items()):
        if len(sample_list) == 1:
            # No duplicates, just update path
            sample = sample_list[0]
            if sample.pdf_storage_path and 'samples/' in sample.pdf_storage_path:
                new_path = sample.pdf_storage_path.replace('samples/', 'uploaded/')
                client.table("dataset_samples").update({
                    "pdf_storage_path": new_path
                }).eq("id", str(sample.id)).execute()
                updated_count += 1
            continue

        # Find the best sample to keep (processed > pending)
        processed = [s for s in sample_list if s.status in [
            SampleStatus.AUTO_VALIDATED,
            SampleStatus.NEEDS_REVIEW,
            SampleStatus.MANUALLY_VALIDATED,
            SampleStatus.ERROR
        ]]

        if processed:
            # Keep the processed one
            to_keep = processed[0]
            to_delete = [s for s in sample_list if s.id != to_keep.id]
        else:
            # Keep the first one
            to_keep = sample_list[0]
            to_delete = sample_list[1:]

        # Update path of kept sample
        if to_keep.pdf_storage_path and 'samples/' in to_keep.pdf_storage_path:
            new_path = to_keep.pdf_storage_path.replace('samples/', 'uploaded/')
            client.table("dataset_samples").update({
                "pdf_storage_path": new_path
            }).eq("id", str(to_keep.id)).execute()
            updated_count += 1

        # Delete duplicates
        for sample in to_delete:
            try:
                client.table("dataset_samples").delete().eq("id", str(sample.id)).execute()
                deleted_count += 1
                print(f"✗ Deleted duplicate: {filename} (ID: {str(sample.id)[:8]}... Status: {sample.status})")
            except Exception as e:
                print(f"⚠ Failed to delete {sample.id}: {e}")

        print(f"✓ Kept: {filename} (ID: {str(to_keep.id)[:8]}... Status: {to_keep.status})")

    print(f"\n{'='*60}")
    print(f"Cleanup complete:")
    print(f"  - {deleted_count} duplicates deleted")
    print(f"  - {updated_count} paths updated to 'uploaded/'")
    print(f"{'='*60}")

if __name__ == "__main__":
    cleanup_duplicates()

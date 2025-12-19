#!/usr/bin/env python3
"""Fix storage paths back to samples/ folder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database.client import get_client

def fix_paths():
    """Update all uploaded/ paths back to samples/."""
    client = get_client()

    # Get all samples with uploaded/ paths
    result = client.table("dataset_samples").select("*").like("pdf_storage_path", "uploaded/%").execute()

    samples = result.data
    print(f"Found {len(samples)} samples with 'uploaded/' paths\n")

    updated = 0
    for sample in samples:
        old_path = sample["pdf_storage_path"]
        new_path = old_path.replace("uploaded/", "samples/")

        try:
            client.table("dataset_samples").update({
                "pdf_storage_path": new_path
            }).eq("id", sample["id"]).execute()

            print(f"✓ {sample['filename']}: {old_path} → {new_path}")
            updated += 1
        except Exception as e:
            print(f"✗ {sample['filename']}: {e}")

    print(f"\n{'='*60}")
    print(f"Updated {updated} paths")
    print(f"{'='*60}")

if __name__ == "__main__":
    fix_paths()

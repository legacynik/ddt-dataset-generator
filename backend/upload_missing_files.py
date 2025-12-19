#!/usr/bin/env python3
"""Upload missing files from local samples/ directory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database.client import get_storage

def upload_missing():
    """Upload missing PDF files."""
    storage = get_storage()
    samples_dir = Path(__file__).parent.parent / "samples"

    missing_files = [
        "testScansione5.pdf",
        "doc01128620251217151633_008.pdf",
        "testScansione3.pdf",
        "testScansione6.pdf",
        "testScansione1.pdf",
        "testScansione2.pdf",
        "testScansione4.pdf",
        "doc01128620251217151633_015.pdf",
        "doc01128620251217151633_013.pdf",
        "doc01128620251217151633_004.pdf",
        "doc01128620251217151633_010.pdf",
    ]

    print("="*60)
    print("UPLOADING MISSING FILES")
    print("="*60)
    print(f"\nLocal directory: {samples_dir}\n")

    uploaded = 0
    failed = 0

    for filename in missing_files:
        local_path = samples_dir / filename

        if not local_path.exists():
            print(f"✗ {filename} - not found locally")
            failed += 1
            continue

        try:
            # Read file
            pdf_bytes = local_path.read_bytes()

            # Upload to storage
            storage_path = f"uploads/{filename}"
            storage.upload(storage_path, pdf_bytes, {"content-type": "application/pdf"})

            print(f"✓ {filename} - uploaded ({len(pdf_bytes)} bytes)")
            uploaded += 1
        except Exception as e:
            print(f"✗ {filename} - error: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"✅ UPLOAD COMPLETE")
    print(f"   Uploaded: {uploaded}")
    print(f"   Failed: {failed}")
    print(f"{'='*60}")

if __name__ == "__main__":
    upload_missing()

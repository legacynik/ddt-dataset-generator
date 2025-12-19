#!/usr/bin/env python3
"""Import previous processing results from markdown report into database.

This script parses DDT_PROCESSING_REPORT.md and creates database records
for all processed samples, allowing manual review and validation.
"""

import re
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import SampleRepository, SampleStatus
from src.database.client import get_client, get_storage

def parse_report(report_path: Path) -> list[dict]:
    """Parse markdown report and extract sample data."""
    content = report_path.read_text()

    # Split by "### N. filename" sections
    sections = re.split(r'\n### \d+\. (.+?\.pdf)\n', content)

    samples = []

    # sections is [header, filename1, content1, filename2, content2, ...]
    for i in range(1, len(sections), 2):
        filename = sections[i]
        section_content = sections[i + 1] if i + 1 < len(sections) else ""

        sample_data = {"filename": filename}

        # Extract file size
        size_match = re.search(r'\*\*File Size:\*\* ([\d.]+) KB', section_content)
        if size_match:
            sample_data["file_size_bytes"] = int(float(size_match.group(1)) * 1024)

        # Extract Datalab JSON
        datalab_match = re.search(r'#### Datalab Extraction\n\n✓ \*\*Success\*\*.*?\n\n```json\n(.*?)\n```', section_content, re.DOTALL)
        if datalab_match:
            try:
                datalab_json = json.loads(datalab_match.group(1))
                # Remove citation fields
                sample_data["datalab_json"] = {
                    k: v for k, v in datalab_json.items()
                    if not k.endswith('_citations')
                }
            except json.JSONDecodeError:
                print(f"⚠ Failed to parse Datalab JSON for {filename}")

        # Extract Azure OCR
        azure_match = re.search(r'#### Azure OCR\n\n✓ \*\*Success\*\*.*?Extracted (\d+) characters', section_content)
        if azure_match:
            sample_data["azure_raw_ocr"] = f"[{azure_match.group(1)} characters extracted]"

        # Extract Gemini JSON
        gemini_match = re.search(r'#### Gemini Extraction\n\n✓ \*\*Success\*\*.*?\n\n```json\n(.*?)\n```', section_content, re.DOTALL)
        if gemini_match:
            try:
                sample_data["gemini_json"] = json.loads(gemini_match.group(1))
            except json.JSONDecodeError:
                print(f"⚠ Failed to parse Gemini JSON for {filename}")
        else:
            gemini_fail = re.search(r'#### Gemini Extraction\n\n✗ \*\*Failed\*\*', section_content)
            if gemini_fail:
                sample_data["gemini_json"] = None
                sample_data["status"] = "error"

        # Extract comparison results
        auto_validated = re.search(r'✓ \*\*AUTO-VALIDATED\*\* - Match Score: \*\*(\d+\.\d+)%\*\*', section_content)
        needs_review = re.search(r'⚠ \*\*NEEDS REVIEW\*\* - Match Score: \*\*(\d+\.\d+)%\*\*', section_content)

        if auto_validated:
            sample_data["status"] = "auto_validated"
            sample_data["match_score"] = float(auto_validated.group(1)) / 100.0
            sample_data["discrepancies"] = []
            sample_data["validated_output"] = sample_data.get("datalab_json")
            sample_data["validation_source"] = "datalab"
        elif needs_review:
            sample_data["status"] = "needs_review"
            sample_data["match_score"] = float(needs_review.group(1)) / 100.0

            # Extract discrepancies
            discrepancies = []
            discrepancy_section = re.search(r'\*\*Discrepancies \(\d+\):\*\*\n\n(.*?)---', section_content, re.DOTALL)
            if discrepancy_section:
                for field_match in re.finditer(r'- \*\*(.+?):\*\*\n  - Datalab: `(.+?)`\n  - Gemini: `(.+?)`', discrepancy_section.group(1)):
                    discrepancies.append({
                        "field": field_match.group(1),
                        "datalab_value": field_match.group(2),
                        "gemini_value": field_match.group(3)
                    })
            sample_data["discrepancies"] = discrepancies
        elif "status" not in sample_data:
            sample_data["status"] = "error"

        if sample_data.get("datalab_json") or sample_data.get("gemini_json"):
            samples.append(sample_data)

    return samples

def check_pdf_exists(filename: str, samples_dir: Path) -> str | None:
    """Check if PDF exists in samples directory."""
    pdf_path = samples_dir / filename
    if pdf_path.exists():
        return str(pdf_path.relative_to(samples_dir.parent.parent))
    return None

def import_samples(samples: list[dict], samples_dir: Path):
    """Import samples into database."""
    repo = SampleRepository()
    storage = get_storage()

    imported = 0
    skipped = 0

    for sample_data in samples:
        filename = sample_data["filename"]

        # Check if already exists
        existing = repo.get_samples(limit=1000)
        if any(s.filename == filename and s.status != SampleStatus.PENDING for s in existing):
            print(f"⊘ {filename} - already imported")
            skipped += 1
            continue

        # Check if PDF exists locally
        pdf_path = check_pdf_exists(filename, samples_dir)
        storage_path = f"samples/{filename}"

        # Upload PDF to storage if exists locally
        if pdf_path:
            try:
                local_path = samples_dir / filename
                pdf_bytes = local_path.read_bytes()
                storage.upload(storage_path, pdf_bytes, {"content-type": "application/pdf"})
                print(f"  ↑ Uploaded to storage: {storage_path}")
            except Exception as e:
                print(f"  ⚠ Failed to upload: {e}")

        # Create database record
        try:
            new_sample = repo.create_sample(
                filename=filename,
                pdf_path=storage_path,
                file_size=sample_data.get("file_size_bytes", 0)
            )

            # Update with processing results
            client = get_client()
            update_data = {
                "status": sample_data.get("status", "needs_review"),
                "datalab_json": sample_data.get("datalab_json"),
                "gemini_json": sample_data.get("gemini_json"),
                "match_score": sample_data.get("match_score"),
                "discrepancies": sample_data.get("discrepancies"),
                "validated_output": sample_data.get("validated_output"),
                "validation_source": sample_data.get("validation_source"),
                "azure_raw_ocr": sample_data.get("azure_raw_ocr"),
                "updated_at": datetime.utcnow().isoformat()
            }

            client.table("dataset_samples").update(update_data).eq("id", str(new_sample.id)).execute()

            status_emoji = "✓" if sample_data.get("status") == "auto_validated" else "⚠"
            print(f"{status_emoji} {filename} - imported ({sample_data.get('status')})")
            imported += 1

        except Exception as e:
            print(f"✗ {filename} - failed: {e}")

    print(f"\n{'='*60}")
    print(f"Import complete: {imported} imported, {skipped} skipped")
    print(f"{'='*60}")

def main():
    """Main entry point."""
    # Find report
    report_path = Path(__file__).parent.parent / "DDT_PROCESSING_REPORT.md"
    samples_dir = Path(__file__).parent.parent / "samples"

    if not report_path.exists():
        print(f"✗ Report not found: {report_path}")
        sys.exit(1)

    print(f"Reading report: {report_path}")
    print(f"Samples directory: {samples_dir}")
    print(f"{'='*60}\n")

    # Parse report
    samples = parse_report(report_path)
    print(f"Found {len(samples)} samples in report\n")

    # Import into database
    import_samples(samples, samples_dir)

if __name__ == "__main__":
    main()

"""Upload all sample PDFs to the API."""

import asyncio
import httpx
from pathlib import Path

API_URL = "http://localhost:8000"
SAMPLES_DIR = Path(__file__).parent.parent / "samples"


async def upload_pdf(client: httpx.AsyncClient, pdf_path: Path) -> dict:
    """Upload a single PDF file."""
    print(f"Uploading {pdf_path.name}...")

    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path.name, f, "application/pdf")}
        response = await client.post(f"{API_URL}/api/upload", files=files)

    if response.status_code == 201:
        data = response.json()
        print(f"  ✓ {pdf_path.name} uploaded successfully (ID: {data['id']})")
        return data
    else:
        print(f"  ✗ Failed to upload {pdf_path.name}: {response.text}")
        return None


async def main():
    """Upload all sample PDFs."""
    pdf_files = sorted(SAMPLES_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {SAMPLES_DIR}")
        return

    print(f"Found {len(pdf_files)} PDF files\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [upload_pdf(client, pdf_path) for pdf_path in pdf_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if r and not isinstance(r, Exception))
    print(f"\n✓ Upload complete: {success_count}/{len(pdf_files)} files uploaded")


if __name__ == "__main__":
    asyncio.run(main())

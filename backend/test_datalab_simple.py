"""Simple test to see Datalab response structure."""

import asyncio
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

from src.extractors import DatalabExtractor

async def test():
    samples_dir = Path(__file__).parent.parent / "samples"
    test_pdf = list(samples_dir.glob("*.pdf"))[0]

    with open(test_pdf, "rb") as f:
        pdf_bytes = f.read()

    extractor = DatalabExtractor(poll_interval=3, max_polls=100)
    result = await extractor.extract(pdf_bytes, filename=test_pdf.name)

    print("SUCCESS:", result.success)
    print("\nEXTRACTED JSON KEYS:", list(result.extracted_json.keys())[:10])
    print("\nJSON STRUCTURE (first 500 chars):")
    print(json.dumps(result.extracted_json, indent=2, ensure_ascii=False)[:500])

if __name__ == "__main__":
    asyncio.run(test())

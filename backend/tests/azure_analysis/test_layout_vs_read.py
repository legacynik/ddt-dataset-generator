"""
Test script to compare Azure Document Intelligence output formats:
- prebuilt-read (current): Only raw text
- prebuilt-layout + markdown: Structured output with tables, figures, checkboxes

Usage:
    SSL_CERT_FILE=/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/certifi/cacert.pem \
    python3 tests/azure_analysis/test_layout_vs_read.py
"""

import requests
import time
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.config import settings
from src.database.client import get_client


def test_layout_markdown(filename: str = 'doc01128620251217151633_008.pdf'):
    """Test Azure Layout with Markdown output on a single document."""

    supabase = get_client()
    endpoint = settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
    key = settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
    api_version = "2024-11-30"

    # Get sample
    result = supabase.table('dataset_samples').select(
        'filename, pdf_storage_path, azure_raw_ocr, datalab_raw_ocr'
    ).eq('filename', filename).execute()

    if not result.data:
        print(f"Document not found: {filename}")
        return

    sample = result.data[0]
    azure_read_len = len(sample.get('azure_raw_ocr') or '')
    datalab_len = len(sample.get('datalab_raw_ocr') or '')

    # Download PDF
    pdf_bytes = supabase.storage.from_('dataset-pdfs').download(sample['pdf_storage_path'])
    print(f"Downloaded {filename}: {len(pdf_bytes)} bytes")

    # Call Azure Layout API with Markdown
    url = f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version={api_version}&outputContentFormat=markdown"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/pdf",
    }

    print(f"Calling Azure Layout API (v{api_version}) with markdown output...")
    response = requests.post(url, headers=headers, data=pdf_bytes)

    if response.status_code != 202:
        print(f"Error: {response.status_code} - {response.text}")
        return

    # Poll for result
    operation_url = response.headers.get("Operation-Location")
    print("Polling for result...")

    for i in range(30):
        time.sleep(2)
        result_response = requests.get(
            operation_url,
            headers={"Ocp-Apim-Subscription-Key": key}
        )
        result_data = result_response.json()
        status = result_data.get("status")

        if status == "succeeded":
            analyze_result = result_data.get("analyzeResult", {})
            content = analyze_result.get("content", "")
            tables = analyze_result.get("tables", [])
            paragraphs = analyze_result.get("paragraphs", [])

            print("\n" + "="*80)
            print("COMPARISON RESULTS")
            print("="*80)
            print(f"\nDocument: {filename}")
            print(f"\nAzure Read (current):     {azure_read_len:>6,} chars")
            print(f"Azure Layout+Markdown:    {len(content):>6,} chars  (+{len(content)/azure_read_len:.1f}x)")
            print(f"Datalab Markdown:         {datalab_len:>6,} chars  (+{datalab_len/azure_read_len:.1f}x)")
            print(f"\nTables extracted: {len(tables)}")
            print(f"Paragraphs: {len(paragraphs)}")

            print("\n" + "-"*80)
            print("MARKDOWN OUTPUT (first 3000 chars):")
            print("-"*80)
            print(content[:3000])
            if len(content) > 3000:
                print("\n...[TRUNCATED]...")

            return content, tables, paragraphs

        elif status == "failed":
            print(f"Failed: {result_data}")
            return None, None, None

    print("Timeout waiting for result")
    return None, None, None


def compare_multiple_documents(limit: int = 5):
    """Compare Azure Read vs Layout+Markdown vs Datalab across multiple documents."""

    supabase = get_client()
    endpoint = settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
    key = settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
    api_version = "2024-11-30"

    # Get samples with both Azure and Datalab OCR
    result = supabase.table('dataset_samples').select(
        'filename, pdf_storage_path, azure_raw_ocr, datalab_raw_ocr'
    ).not_.is_('azure_raw_ocr', 'null').limit(limit).execute()

    print("="*100)
    print("COMPARISON: Azure Read vs Azure Layout+Markdown vs Datalab")
    print("="*100)
    print()

    for sample in result.data:
        filename = sample['filename']
        azure_read_len = len(sample.get('azure_raw_ocr') or '')
        datalab_len = len(sample.get('datalab_raw_ocr') or '')

        # Download PDF
        pdf_bytes = supabase.storage.from_('dataset-pdfs').download(sample['pdf_storage_path'])

        # Call Layout API
        url = f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version={api_version}&outputContentFormat=markdown"
        headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/pdf"}

        response = requests.post(url, headers=headers, data=pdf_bytes)
        if response.status_code == 202:
            operation_url = response.headers.get("Operation-Location")

            for i in range(30):
                time.sleep(2)
                result_response = requests.get(
                    operation_url,
                    headers={"Ocp-Apim-Subscription-Key": key}
                )
                result_data = result_response.json()

                if result_data.get("status") == "succeeded":
                    analyze_result = result_data.get("analyzeResult", {})
                    layout_content = analyze_result.get("content", "")
                    tables = len(analyze_result.get("tables", []))
                    paragraphs = len(analyze_result.get("paragraphs", []))

                    ratio_layout = len(layout_content) / azure_read_len if azure_read_len > 0 else 0
                    ratio_datalab = datalab_len / azure_read_len if azure_read_len > 0 else 0

                    print(f"📄 {filename}")
                    print(f"   Azure Read (current):     {azure_read_len:>6,} chars")
                    print(f"   Azure Layout+Markdown:    {len(layout_content):>6,} chars  (+{ratio_layout:.1f}x) | {tables} tables, {paragraphs} paragraphs")
                    print(f"   Datalab Markdown:         {datalab_len:>6,} chars  (+{ratio_datalab:.1f}x)")
                    print()
                    break
                elif result_data.get("status") == "failed":
                    print(f"❌ {filename}: Layout failed")
                    break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Azure Layout vs Read OCR")
    parser.add_argument("--file", type=str, help="Single file to test")
    parser.add_argument("--compare", type=int, default=5, help="Compare N documents")

    args = parser.parse_args()

    if args.file:
        test_layout_markdown(args.file)
    else:
        compare_multiple_documents(args.compare)

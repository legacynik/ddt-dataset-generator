"""Process all sample PDFs and generate comparison report.

This script:
1. Processes all PDFs in ../samples/ directory
2. Runs full extraction pipeline (Datalab + Azure + Gemini)
3. Compares outputs using match score algorithm
4. Generates detailed Markdown report

Usage:
    python process_samples.py
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from src.extractors import DatalabExtractor, AzureOCRExtractor, GeminiExtractor
from src.processing.comparison import calculate_match_score

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def process_pdf(
    pdf_path: Path,
    datalab: DatalabExtractor,
    azure: AzureOCRExtractor,
    gemini: GeminiExtractor
) -> Dict[str, Any]:
    """Process a single PDF through the complete pipeline.

    Args:
        pdf_path: Path to PDF file
        datalab: Datalab extractor instance
        azure: Azure OCR extractor instance
        gemini: Gemini extractor instance

    Returns:
        Dict with all extraction results and comparison
    """
    start_time = time.time()

    logger.info(f"\n{'='*80}")
    logger.info(f"Processing: {pdf_path.name}")
    logger.info(f"{'='*80}")

    # Read PDF
    pdf_bytes = pdf_path.read_bytes()

    result = {
        "filename": pdf_path.name,
        "file_size_kb": len(pdf_bytes) / 1024,
        "total_time_ms": 0,
        "datalab": {},
        "azure": {},
        "gemini": {},
        "comparison": {},
        "errors": []
    }

    # Step 1: Datalab extraction
    logger.info("[1/3] Running Datalab extraction...")
    try:
        datalab_result = await datalab.extract(pdf_bytes, pdf_path.name)
        result["datalab"] = {
            "success": datalab_result.success,
            "time_ms": datalab_result.processing_time_ms,
            "extracted_json": datalab_result.extracted_json if datalab_result.success else None,
            "error": datalab_result.error_message,
        }
        if datalab_result.success:
            logger.info(f"✓ Datalab completed in {datalab_result.processing_time_ms}ms")
        else:
            logger.error(f"✗ Datalab failed: {datalab_result.error_message}")
    except Exception as e:
        logger.error(f"✗ Datalab exception: {e}")
        result["datalab"]["success"] = False
        result["datalab"]["error"] = str(e)
        result["errors"].append(f"Datalab: {e}")

    # Step 2: Azure OCR
    logger.info("[2/3] Running Azure OCR...")
    try:
        azure_result = await azure.extract(pdf_bytes, pdf_path.name)
        result["azure"] = {
            "success": azure_result.success,
            "time_ms": azure_result.processing_time_ms,
            "text_length": len(azure_result.raw_text) if azure_result.success else 0,
            "error": azure_result.error_message,
        }
        if azure_result.success:
            logger.info(f"✓ Azure completed in {azure_result.processing_time_ms}ms ({len(azure_result.raw_text)} chars)")
        else:
            logger.error(f"✗ Azure failed: {azure_result.error_message}")
    except Exception as e:
        logger.error(f"✗ Azure exception: {e}")
        result["azure"]["success"] = False
        result["azure"]["error"] = str(e)
        result["errors"].append(f"Azure: {e}")

    # Step 3: Gemini extraction (only if Azure succeeded)
    logger.info("[3/3] Running Gemini extraction...")
    if result["azure"]["success"] and azure_result.raw_text:
        try:
            gemini_result = await gemini.extract(azure_result.raw_text, pdf_path.name)
            result["gemini"] = {
                "success": gemini_result.success,
                "time_ms": gemini_result.processing_time_ms,
                "extracted_json": gemini_result.extracted_json if gemini_result.success else None,
                "error": gemini_result.error_message,
            }
            if gemini_result.success:
                logger.info(f"✓ Gemini completed in {gemini_result.processing_time_ms}ms")
            else:
                logger.error(f"✗ Gemini failed: {gemini_result.error_message}")
        except Exception as e:
            logger.error(f"✗ Gemini exception: {e}")
            result["gemini"]["success"] = False
            result["gemini"]["error"] = str(e)
            result["errors"].append(f"Gemini: {e}")
    else:
        logger.warning("⚠ Skipping Gemini (Azure failed)")
        result["gemini"]["success"] = False
        result["gemini"]["error"] = "Skipped due to Azure failure"

    # Step 4: Comparison (if both Datalab and Gemini succeeded)
    if result["datalab"]["success"] and result["gemini"]["success"]:
        try:
            datalab_json = result["datalab"]["extracted_json"]
            gemini_json = result["gemini"]["extracted_json"]

            match_score, discrepancies = calculate_match_score(datalab_json, gemini_json)

            result["comparison"] = {
                "match_score": match_score,
                "discrepancies": discrepancies,
                "auto_validated": match_score >= 0.95,
            }

            status = "✓ AUTO-VALIDATED" if match_score >= 0.95 else "⚠ NEEDS REVIEW"
            logger.info(f"{status} - Match score: {match_score:.2%} ({len(discrepancies)} discrepancies)")
        except Exception as e:
            logger.error(f"✗ Comparison exception: {e}")
            result["errors"].append(f"Comparison: {e}")
    else:
        logger.warning("⚠ Skipping comparison (one or both extractors failed)")

    # Calculate total time
    result["total_time_ms"] = int((time.time() - start_time) * 1000)
    logger.info(f"Total processing time: {result['total_time_ms']}ms")

    return result


def generate_markdown_report(results: List[Dict[str, Any]], output_path: Path):
    """Generate detailed Markdown report comparing all PDFs.

    Args:
        results: List of processing results
        output_path: Path to output MD file
    """
    logger.info(f"\nGenerating Markdown report: {output_path}")

    with open(output_path, "w", encoding="utf-8") as f:
        # Header
        f.write("# DDT Processing Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total PDFs Processed:** {len(results)}\n\n")

        # Summary statistics
        f.write("## Summary Statistics\n\n")

        total_pdfs = len(results)
        datalab_success = sum(1 for r in results if r["datalab"].get("success"))
        azure_success = sum(1 for r in results if r["azure"].get("success"))
        gemini_success = sum(1 for r in results if r["gemini"].get("success"))
        auto_validated = sum(1 for r in results if r["comparison"].get("auto_validated"))
        needs_review = sum(1 for r in results if r["comparison"] and not r["comparison"].get("auto_validated"))

        f.write(f"- **Total PDFs:** {total_pdfs}\n")
        f.write(f"- **Datalab Success:** {datalab_success}/{total_pdfs} ({datalab_success/total_pdfs*100:.1f}%)\n")
        f.write(f"- **Azure Success:** {azure_success}/{total_pdfs} ({azure_success/total_pdfs*100:.1f}%)\n")
        f.write(f"- **Gemini Success:** {gemini_success}/{total_pdfs} ({gemini_success/total_pdfs*100:.1f}%)\n")
        f.write(f"- **Auto-Validated:** {auto_validated}/{total_pdfs} ({auto_validated/total_pdfs*100:.1f}%)\n")
        f.write(f"- **Needs Review:** {needs_review}/{total_pdfs} ({needs_review/total_pdfs*100:.1f}%)\n\n")

        # Average times
        avg_datalab_time = sum(r["datalab"].get("time_ms", 0) for r in results if r["datalab"].get("success")) / max(datalab_success, 1)
        avg_azure_time = sum(r["azure"].get("time_ms", 0) for r in results if r["azure"].get("success")) / max(azure_success, 1)
        avg_gemini_time = sum(r["gemini"].get("time_ms", 0) for r in results if r["gemini"].get("success")) / max(gemini_success, 1)
        avg_total_time = sum(r["total_time_ms"] for r in results) / total_pdfs

        f.write("### Average Processing Times\n\n")
        f.write(f"- **Datalab:** {avg_datalab_time/1000:.1f}s\n")
        f.write(f"- **Azure OCR:** {avg_azure_time/1000:.1f}s\n")
        f.write(f"- **Gemini:** {avg_gemini_time/1000:.1f}s\n")
        f.write(f"- **Total (per PDF):** {avg_total_time/1000:.1f}s\n\n")

        # Quick overview table
        f.write("## Quick Overview\n\n")
        f.write("| Filename | Size (KB) | Datalab | Gemini | Match Score | Status |\n")
        f.write("|----------|-----------|---------|--------|-------------|--------|\n")

        for r in results:
            filename = r["filename"]
            size = f"{r['file_size_kb']:.1f}"
            datalab_status = "✓" if r["datalab"].get("success") else "✗"
            gemini_status = "✓" if r["gemini"].get("success") else "✗"

            if r["comparison"]:
                match_score = f"{r['comparison']['match_score']:.2%}"
                status = "✓ Auto" if r["comparison"]["auto_validated"] else "⚠ Review"
            else:
                match_score = "N/A"
                status = "✗ Error"

            f.write(f"| {filename} | {size} | {datalab_status} | {gemini_status} | {match_score} | {status} |\n")

        f.write("\n---\n\n")

        # Detailed results for each PDF
        f.write("## Detailed Results\n\n")

        for idx, r in enumerate(results, 1):
            f.write(f"### {idx}. {r['filename']}\n\n")

            # File info
            f.write(f"**File Size:** {r['file_size_kb']:.1f} KB  \n")
            f.write(f"**Total Processing Time:** {r['total_time_ms']/1000:.1f}s\n\n")

            # Datalab results
            f.write("#### Datalab Extraction\n\n")
            if r["datalab"].get("success"):
                f.write(f"✓ **Success** ({r['datalab']['time_ms']/1000:.1f}s)\n\n")
                f.write("```json\n")
                f.write(json.dumps(r["datalab"]["extracted_json"], ensure_ascii=False, indent=2))
                f.write("\n```\n\n")
            else:
                f.write(f"✗ **Failed**\n\n")
                f.write(f"Error: `{r['datalab'].get('error', 'Unknown error')}`\n\n")

            # Azure results
            f.write("#### Azure OCR\n\n")
            if r["azure"].get("success"):
                f.write(f"✓ **Success** ({r['azure']['time_ms']/1000:.1f}s)  \n")
                f.write(f"Extracted {r['azure']['text_length']} characters\n\n")
            else:
                f.write(f"✗ **Failed**\n\n")
                f.write(f"Error: `{r['azure'].get('error', 'Unknown error')}`\n\n")

            # Gemini results
            f.write("#### Gemini Extraction\n\n")
            if r["gemini"].get("success"):
                f.write(f"✓ **Success** ({r['gemini']['time_ms']/1000:.1f}s)\n\n")
                f.write("```json\n")
                f.write(json.dumps(r["gemini"]["extracted_json"], ensure_ascii=False, indent=2))
                f.write("\n```\n\n")
            else:
                f.write(f"✗ **Failed**\n\n")
                f.write(f"Error: `{r['gemini'].get('error', 'Unknown error')}`\n\n")

            # Comparison
            f.write("#### Comparison (Datalab vs Gemini)\n\n")
            if r["comparison"]:
                match_score = r["comparison"]["match_score"]
                discrepancies = r["comparison"]["discrepancies"]
                auto_validated = r["comparison"]["auto_validated"]

                if auto_validated:
                    f.write(f"✓ **AUTO-VALIDATED** - Match Score: **{match_score:.2%}**\n\n")
                else:
                    f.write(f"⚠ **NEEDS REVIEW** - Match Score: **{match_score:.2%}**\n\n")

                if discrepancies:
                    f.write(f"**Discrepancies ({len(discrepancies)}):**\n\n")

                    # Show field-by-field comparison for discrepancies
                    for field in discrepancies:
                        datalab_val = r["datalab"]["extracted_json"].get(field)
                        gemini_val = r["gemini"]["extracted_json"].get(field)

                        f.write(f"- **{field}:**\n")
                        f.write(f"  - Datalab: `{datalab_val}`\n")
                        f.write(f"  - Gemini: `{gemini_val}`\n")
                else:
                    f.write("✓ All fields match!\n\n")
            else:
                f.write("⚠ Comparison not available (one or both extractors failed)\n\n")

            # Errors
            if r["errors"]:
                f.write("#### Errors\n\n")
                for error in r["errors"]:
                    f.write(f"- {error}\n")
                f.write("\n")

            f.write("---\n\n")

    logger.info(f"✓ Report generated: {output_path}")


async def main():
    """Main processing function."""
    # Find all PDFs in samples directory
    samples_dir = Path(__file__).parent.parent / "samples"

    if not samples_dir.exists():
        logger.error(f"Samples directory not found: {samples_dir}")
        return

    pdf_files = sorted(samples_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error(f"No PDF files found in {samples_dir}")
        return

    logger.info(f"Found {len(pdf_files)} PDF files to process\n")

    # Initialize extractors
    datalab = DatalabExtractor(poll_interval=3, max_polls=100)
    azure = AzureOCRExtractor(timeout=60, max_retries=3)
    gemini = GeminiExtractor(max_retries=2, timeout=60)

    # Process all PDFs
    results = []

    for pdf_path in pdf_files:
        result = await process_pdf(pdf_path, datalab, azure, gemini)
        results.append(result)

        # Small delay between PDFs to respect rate limits
        await asyncio.sleep(2)

    # Generate report
    output_path = Path(__file__).parent.parent / "DDT_PROCESSING_REPORT.md"
    generate_markdown_report(results, output_path)

    logger.info("\n" + "="*80)
    logger.info("✓ All PDFs processed successfully!")
    logger.info(f"✓ Report saved to: {output_path}")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python
"""Integration test for database layer.

This script tests the database layer with a real Supabase instance.
Run this manually to verify the database setup is working correctly.

Usage:
    python test_integration_db.py
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import (
    SampleRepository,
    SampleStatus,
    StatsRepository,
    get_client,
    upload_pdf,
    get_pdf_url,
    delete_pdf,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_connection():
    """Test basic Supabase connection."""
    logger.info("Testing Supabase connection...")
    try:
        client = get_client()
        logger.info(f"✓ Connection successful: {client}")
        return True
    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
        return False


def test_stats_repository():
    """Test StatsRepository operations."""
    logger.info("\nTesting StatsRepository...")
    try:
        repo = StatsRepository()

        # Get current stats
        stats = repo.get_stats()
        logger.info(f"✓ Current stats: {stats.total_samples} total, {stats.processed} processed")

        # Test incrementing counters (we'll revert this)
        original_total = stats.total_samples
        stats = repo.increment_counters(total_samples=1)
        logger.info(f"✓ Incremented total_samples: {stats.total_samples}")

        # Revert the change
        stats = repo.update_stats(total_samples=original_total)
        logger.info(f"✓ Reverted to original: {stats.total_samples}")

        return True
    except Exception as e:
        logger.error(f"✗ StatsRepository test failed: {e}")
        return False


def test_sample_repository():
    """Test SampleRepository operations."""
    logger.info("\nTesting SampleRepository...")
    try:
        repo = SampleRepository()

        # Create a test sample
        logger.info("Creating test sample...")
        sample = repo.create_sample(
            filename="test_integration.pdf",
            pdf_path="uploads/test_integration.pdf",
            file_size=1024
        )
        logger.info(f"✓ Sample created with ID: {sample.id}")

        # Get the sample back
        retrieved = repo.get_sample(sample.id)
        assert retrieved is not None
        assert retrieved.filename == "test_integration.pdf"
        logger.info(f"✓ Sample retrieved successfully")

        # Update the sample
        updated = repo.update_sample(
            sample.id,
            status=SampleStatus.PROCESSING,
            datalab_raw_ocr="Test OCR text"
        )
        assert updated.status == SampleStatus.PROCESSING
        logger.info(f"✓ Sample updated successfully")

        # List samples
        samples = repo.get_samples(limit=5)
        logger.info(f"✓ Retrieved {len(samples)} samples")

        # Count by status
        counts = repo.count_by_status()
        logger.info(f"✓ Status counts: {counts}")

        # Clean up: update to rejected so it doesn't affect real data
        repo.update_sample(sample.id, status=SampleStatus.REJECTED)
        logger.info(f"✓ Test sample marked as rejected")

        return True
    except Exception as e:
        logger.error(f"✗ SampleRepository test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_storage():
    """Test Storage operations."""
    logger.info("\nTesting Storage operations...")
    try:
        # Create fake PDF content
        pdf_content = b"%PDF-1.4\nFake PDF for testing\n%%EOF"

        # Upload
        logger.info("Uploading test PDF...")
        storage_path = upload_pdf(pdf_content, "test_storage.pdf")
        logger.info(f"✓ PDF uploaded to: {storage_path}")

        # Get signed URL
        logger.info("Getting signed URL...")
        url = get_pdf_url(storage_path, expires_in=60)
        assert url.startswith("https://")
        logger.info(f"✓ Signed URL generated: {url[:50]}...")

        # Delete (cleanup)
        logger.info("Deleting test PDF...")
        success = delete_pdf(storage_path)
        if success:
            logger.info(f"✓ PDF deleted successfully")
        else:
            logger.warning(f"⚠ PDF deletion returned False (may not exist)")

        return True
    except Exception as e:
        logger.error(f"✗ Storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    logger.info("=" * 60)
    logger.info("Starting Database Integration Tests")
    logger.info("=" * 60)

    results = {
        "Connection": test_connection(),
        "StatsRepository": test_stats_repository(),
        "SampleRepository": test_sample_repository(),
        "Storage": test_storage(),
    }

    logger.info("\n" + "=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name:.<40} {status}")

    all_passed = all(results.values())

    if all_passed:
        logger.info("\n🎉 All tests passed!")
        return 0
    else:
        logger.error("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Unit tests for Alpaca formatter.

Tests:
- format_to_alpaca(): Sample to Alpaca conversion
- split_dataset(): Train/validation split
- calculate_field_coverage(): Field coverage statistics
- generate_quality_report(): Quality metrics
- export_dataset(): JSONL export with train/val split
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

from src.processing.alpaca_formatter import (
    format_to_alpaca,
    split_dataset,
    calculate_field_coverage,
    generate_quality_report,
    export_dataset,
    ALPACA_INSTRUCTION,
)


class TestFormatToAlpaca:
    """Tests for format_to_alpaca function."""

    def test_format_with_azure_ocr(self):
        """Should format sample with Azure OCR as input."""
        # Create mock sample
        sample = Mock()
        sample.id = "test-123"
        sample.azure_raw_ocr = "LAVAZZA\nLUIGI LAVAZZA S.p.A.\nDDT N. 123"
        sample.datalab_raw_ocr = "Different OCR text"
        sample.validated_output = {
            "mittente": "LAVAZZA",
            "destinatario": "CONAD",
            "numero_documento": "123"
        }

        result = format_to_alpaca(sample, ocr_source="azure")

        assert result is not None
        assert result["instruction"] == ALPACA_INSTRUCTION
        assert result["input"] == "LAVAZZA\nLUIGI LAVAZZA S.p.A.\nDDT N. 123"
        assert "LAVAZZA" in result["output"]
        assert "CONAD" in result["output"]

        # Output should be valid JSON
        output_json = json.loads(result["output"])
        assert output_json["mittente"] == "LAVAZZA"

    def test_format_with_datalab_ocr(self):
        """Should format sample with Datalab OCR as input."""
        sample = Mock()
        sample.id = "test-123"
        sample.azure_raw_ocr = "Azure OCR text"
        sample.datalab_raw_ocr = "DATALAB\nOCR TEXT\nDDT 456"
        sample.validated_output = {
            "mittente": "BARILLA",
            "numero_documento": "456"
        }

        result = format_to_alpaca(sample, ocr_source="datalab")

        assert result is not None
        assert result["input"] == "DATALAB\nOCR TEXT\nDDT 456"
        assert "BARILLA" in result["output"]

    def test_format_with_no_validated_output(self):
        """Should return None if sample has no validated_output."""
        sample = Mock()
        sample.id = "test-123"
        sample.azure_raw_ocr = "Some OCR text"
        sample.validated_output = None

        result = format_to_alpaca(sample, ocr_source="azure")

        assert result is None

    def test_format_with_empty_ocr(self):
        """Should return None if OCR text is empty."""
        sample = Mock()
        sample.id = "test-123"
        sample.azure_raw_ocr = ""
        sample.validated_output = {"mittente": "TEST"}

        result = format_to_alpaca(sample, ocr_source="azure")

        assert result is None

    def test_format_with_invalid_ocr_source(self):
        """Should raise ValueError for invalid ocr_source."""
        sample = Mock()
        sample.azure_raw_ocr = "Text"
        sample.validated_output = {"mittente": "TEST"}  # Non-empty validated_output

        with pytest.raises(ValueError, match="Invalid ocr_source"):
            format_to_alpaca(sample, ocr_source="invalid")

    def test_output_preserves_utf8(self):
        """Should preserve UTF-8 characters without escaping."""
        sample = Mock()
        sample.id = "test-123"
        sample.azure_raw_ocr = "DDT Italiano"
        sample.validated_output = {
            "mittente": "SOCIETÀ S.p.A.",
            "destinatario": "Società Cooperativa",
            "indirizzo_destinazione_completo": "Via è à ò ù"
        }

        result = format_to_alpaca(sample, ocr_source="azure")

        # UTF-8 chars should be preserved (not escaped)
        assert "SOCIETÀ" in result["output"]
        assert "è à ò ù" in result["output"]


class TestSplitDataset:
    """Tests for split_dataset function."""

    def test_split_default_ratio(self):
        """Should split 93% train, 7% validation by default."""
        samples = [Mock() for _ in range(100)]

        train, val = split_dataset(samples)

        assert len(train) == 93
        assert len(val) == 7

    def test_split_custom_ratio(self):
        """Should respect custom validation_ratio."""
        samples = [Mock() for _ in range(100)]

        train, val = split_dataset(samples, validation_ratio=0.2)

        assert len(train) == 80
        assert len(val) == 20

    def test_split_small_dataset(self):
        """Should have at least 1 validation sample."""
        samples = [Mock() for _ in range(5)]

        train, val = split_dataset(samples, validation_ratio=0.1)

        assert len(val) >= 1
        assert len(train) + len(val) == 5

    def test_split_empty_dataset(self):
        """Should handle empty dataset."""
        samples = []

        train, val = split_dataset(samples)

        assert len(train) == 0
        assert len(val) == 0

    def test_split_reproducibility(self):
        """Should produce same split with same seed."""
        samples = [Mock(id=i) for i in range(50)]

        train1, val1 = split_dataset(samples, random_seed=42)
        train2, val2 = split_dataset(samples, random_seed=42)

        # Same split
        assert [s.id for s in train1] == [s.id for s in train2]
        assert [s.id for s in val1] == [s.id for s in val2]

    def test_split_different_seeds(self):
        """Should produce different splits with different seeds."""
        samples = [Mock(id=i) for i in range(50)]

        train1, val1 = split_dataset(samples, random_seed=42)
        train2, val2 = split_dataset(samples, random_seed=100)

        # Different splits
        assert [s.id for s in train1] != [s.id for s in train2]


class TestCalculateFieldCoverage:
    """Tests for calculate_field_coverage function."""

    def test_full_coverage(self):
        """All samples have all fields."""
        samples = [
            Mock(validated_output={
                "mittente": "A",
                "destinatario": "B",
                "indirizzo_destinazione_completo": "C",
                "data_documento": "2025-01-01",
                "data_trasporto": "2025-01-02",
                "numero_documento": "123",
                "numero_ordine": "ORD-1",
                "codice_cliente": "CLI-1",
            })
            for _ in range(10)
        ]

        coverage = calculate_field_coverage(samples)

        # All fields should have 100% coverage
        for field, ratio in coverage.items():
            assert ratio == 1.0

    def test_partial_coverage(self):
        """Some samples missing some fields."""
        samples = [
            Mock(validated_output={
                "mittente": "A",
                "destinatario": "B",
                "numero_documento": "123",
                "numero_ordine": None,  # Missing
                "codice_cliente": "",   # Empty
                "indirizzo_destinazione_completo": "Addr",
                "data_documento": "2025-01-01",
                "data_trasporto": "2025-01-02",
            })
            for _ in range(10)
        ]

        coverage = calculate_field_coverage(samples)

        # numero_ordine and codice_cliente should be 0% (None/empty)
        assert coverage["numero_ordine"] == 0.0
        assert coverage["codice_cliente"] == 0.0

        # Others should be 100%
        assert coverage["mittente"] == 1.0
        assert coverage["destinatario"] == 1.0

    def test_empty_samples(self):
        """Should handle empty sample list."""
        coverage = calculate_field_coverage([])

        assert coverage == {}


class TestGenerateQualityReport:
    """Tests for generate_quality_report function."""

    def test_quality_report_structure(self):
        """Should return report with all required fields."""
        samples = [
            Mock(
                azure_raw_ocr="OCR text" * 100,
                datalab_raw_ocr="Different text",
                validated_output={
                    "mittente": "A",
                    "destinatario": "B",
                    "numero_documento": "123",
                    "numero_ordine": "ORD-1",
                    "codice_cliente": "CLI-1",
                    "indirizzo_destinazione_completo": "Addr",
                    "data_documento": "2025-01-01",
                    "data_trasporto": "2025-01-02",
                }
            )
            for _ in range(10)
        ]

        report = generate_quality_report(samples, ocr_source="azure")

        assert "total_samples" in report
        assert "field_coverage" in report
        assert "avg_ocr_length" in report
        assert "avg_output_length" in report
        assert "missing_fields_count" in report
        assert "quality_score" in report

        assert report["total_samples"] == 10
        assert report["quality_score"] == 1.0  # All fields present

    def test_quality_report_empty(self):
        """Should handle empty sample list."""
        report = generate_quality_report([])

        assert report["total_samples"] == 0
        assert report["quality_score"] == 0.0


class TestExportDataset:
    """Tests for export_dataset function."""

    def test_export_creates_files(self):
        """Should create train.jsonl, validation.jsonl, quality_report.json."""
        # Create mock samples
        mock_samples = []
        for i in range(20):
            sample = Mock()
            sample.id = f"sample-{i}"
            sample.azure_raw_ocr = f"OCR text for sample {i}"
            sample.datalab_raw_ocr = f"Datalab OCR {i}"
            sample.validated_output = {
                "mittente": f"Company {i}",
                "destinatario": f"Customer {i}",
                "numero_documento": f"DDT-{i}",
                "numero_ordine": f"ORD-{i}",
                "codice_cliente": f"CLI-{i}",
                "indirizzo_destinazione_completo": f"Address {i}",
                "data_documento": "2025-01-15",
                "data_trasporto": "2025-01-16",
            }
            mock_samples.append(sample)

        # Create mock repository
        mock_repo = Mock()
        mock_repo.get_samples = Mock(side_effect=[
            mock_samples,  # AUTO_VALIDATED
            []             # MANUALLY_VALIDATED
        ])

        # Export to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            stats = export_dataset(
                output_dir=output_dir,
                ocr_source="azure",
                validation_ratio=0.2,
                sample_repo=mock_repo
            )

            # Check files exist
            assert (output_dir / "train.jsonl").exists()
            assert (output_dir / "validation.jsonl").exists()
            assert (output_dir / "quality_report.json").exists()

            # Check stats
            assert stats.total_samples == 20
            assert stats.train_samples == 16  # 80%
            assert stats.validation_samples == 4  # 20%
            assert stats.ocr_source == "azure"

            # Validate JSONL format
            with open(output_dir / "train.jsonl", "r", encoding="utf-8") as f:
                for line in f:
                    obj = json.loads(line)
                    assert "instruction" in obj
                    assert "input" in obj
                    assert "output" in obj
                    assert obj["instruction"] == ALPACA_INSTRUCTION

            # Validate quality report
            with open(output_dir / "quality_report.json", "r", encoding="utf-8") as f:
                report = json.load(f)
                assert report["total_samples"] == 20
                assert "field_coverage" in report

    def test_export_with_no_samples(self):
        """Should handle case with no validated samples."""
        mock_repo = Mock()
        mock_repo.get_samples = Mock(return_value=[])

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            stats = export_dataset(
                output_dir=output_dir,
                sample_repo=mock_repo
            )

            assert stats.total_samples == 0
            assert stats.train_samples == 0
            assert stats.validation_samples == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

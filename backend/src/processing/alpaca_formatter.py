"""Alpaca format export for DDT dataset generation.

This module converts validated DDT samples into Alpaca JSONL format
for fine-tuning LLMs with LLaMA Factory.

Alpaca Format:
{
    "instruction": "<task description>",
    "input": "<raw OCR text>",
    "output": "<structured JSON>"
}

Features:
- Train/validation split (93%/7%)
- Quality report generation
- JSONL export with UTF-8 encoding
"""

import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from src.database import SampleRepository, SampleStatus

logger = logging.getLogger(__name__)


# Instruction prompt (fixed for all samples)
ALPACA_INSTRUCTION = (
    "Estrai i dati strutturati dal seguente DDT italiano. "
    "Campi richiesti: mittente, destinatario, indirizzo_destinazione_completo, "
    "data_documento, data_trasporto, numero_documento, numero_ordine, codice_cliente. "
    "Rispondi con JSON valido."
)


@dataclass
class ExportStats:
    """Statistics from dataset export."""

    total_samples: int
    train_samples: int
    validation_samples: int
    ocr_source: str
    field_coverage: Dict[str, float]  # Field name -> percentage of samples with value
    avg_ocr_length: int
    avg_output_length: int


def format_to_alpaca(
    sample,
    ocr_source: str = "azure"
) -> Optional[Dict[str, str]]:
    """Convert a sample to Alpaca format.

    Args:
        sample: DatasetSample from database
        ocr_source: "azure" or "datalab" - which OCR to use as input

    Returns:
        Dict with instruction, input, output, or None if sample cannot be formatted

    Example:
        >>> sample = repo.get_sample("abc-123")
        >>> alpaca_dict = format_to_alpaca(sample, ocr_source="azure")
        >>> alpaca_dict
        {
            "instruction": "Estrai i dati...",
            "input": "LAVAZZA\\nLUIGI LAVAZZA...",
            "output": '{"mittente": "LAVAZZA", ...}'
        }
    """
    # Validate sample has required data
    if not sample.validated_output:
        logger.warning(f"Sample {sample.id} has no validated_output, skipping")
        return None

    # Choose OCR source
    if ocr_source == "azure":
        input_text = sample.azure_raw_ocr
    elif ocr_source == "datalab":
        input_text = sample.datalab_raw_ocr
    else:
        raise ValueError(f"Invalid ocr_source: {ocr_source}. Must be 'azure' or 'datalab'")

    # Validate OCR text exists
    if not input_text or not input_text.strip():
        logger.warning(
            f"Sample {sample.id} has no {ocr_source}_raw_ocr, skipping"
        )
        return None

    # Format output as JSON string (without escape sequences for better readability)
    output_text = json.dumps(sample.validated_output, ensure_ascii=False)

    return {
        "instruction": ALPACA_INSTRUCTION,
        "input": input_text.strip(),
        "output": output_text,
    }


def split_dataset(
    samples: List,
    validation_ratio: float = 0.07,
    random_seed: int = 42
) -> Tuple[List, List]:
    """Split dataset into training and validation sets.

    Uses random shuffle with fixed seed for reproducibility.
    Default split: 93% training, 7% validation.

    Args:
        samples: List of samples to split
        validation_ratio: Ratio of validation samples (default: 0.07 = 7%)
        random_seed: Random seed for reproducibility (default: 42)

    Returns:
        Tuple of (training_samples, validation_samples)

    Example:
        >>> samples = repo.get_samples(status=SampleStatus.AUTO_VALIDATED)
        >>> train, val = split_dataset(samples, validation_ratio=0.07)
        >>> len(train), len(val)
        (93, 7)  # for 100 samples
    """
    # Shuffle with fixed seed for reproducibility
    shuffled = samples.copy()
    random.seed(random_seed)
    random.shuffle(shuffled)

    # Calculate split index (at least 1 validation sample if possible)
    val_size = max(1, int(len(shuffled) * validation_ratio)) if len(shuffled) > 0 else 0

    # Split
    validation = shuffled[:val_size]
    training = shuffled[val_size:]

    logger.info(
        f"Split dataset: {len(training)} training, {len(validation)} validation "
        f"({validation_ratio*100:.1f}% validation)"
    )

    return training, validation


def calculate_field_coverage(samples: List) -> Dict[str, float]:
    """Calculate percentage of samples with each field populated.

    Args:
        samples: List of samples

    Returns:
        Dict mapping field name to coverage percentage (0.0-1.0)

    Example:
        >>> coverage = calculate_field_coverage(samples)
        >>> coverage
        {
            "mittente": 1.0,
            "destinatario": 1.0,
            "numero_documento": 0.95,
            "numero_ordine": 0.60,  # Often missing
            ...
        }
    """
    if not samples:
        return {}

    fields = [
        "mittente",
        "destinatario",
        "indirizzo_destinazione_completo",
        "data_documento",
        "data_trasporto",
        "numero_documento",
        "numero_ordine",
        "codice_cliente",
    ]

    coverage = {}
    total_samples = len(samples)

    for field in fields:
        count = 0
        for sample in samples:
            value = sample.validated_output.get(field) if sample.validated_output else None
            if value is not None and str(value).strip():
                count += 1

        coverage[field] = count / total_samples if total_samples > 0 else 0.0

    return coverage


def generate_quality_report(samples: List, ocr_source: str = "azure") -> Dict:
    """Generate quality metrics report for dataset.

    Includes:
    - Field coverage statistics
    - Average OCR/output lengths
    - Sample counts and distribution

    Args:
        samples: List of samples to analyze
        ocr_source: OCR source used for input

    Returns:
        Dict with quality metrics

    Example:
        >>> report = generate_quality_report(samples)
        >>> report
        {
            "total_samples": 100,
            "field_coverage": {"mittente": 1.0, ...},
            "avg_ocr_length": 1500,
            "avg_output_length": 250,
            "missing_fields_count": 5,
            "quality_score": 0.95
        }
    """
    if not samples:
        return {
            "total_samples": 0,
            "field_coverage": {},
            "avg_ocr_length": 0,
            "avg_output_length": 0,
            "missing_fields_count": 0,
            "quality_score": 0.0,
        }

    # Calculate field coverage
    coverage = calculate_field_coverage(samples)

    # Calculate average lengths
    ocr_lengths = []
    output_lengths = []

    for sample in samples:
        # OCR length
        if ocr_source == "azure" and sample.azure_raw_ocr:
            ocr_lengths.append(len(sample.azure_raw_ocr))
        elif ocr_source == "datalab" and sample.datalab_raw_ocr:
            ocr_lengths.append(len(sample.datalab_raw_ocr))

        # Output length
        if sample.validated_output:
            output_text = json.dumps(sample.validated_output, ensure_ascii=False)
            output_lengths.append(len(output_text))

    avg_ocr_length = int(sum(ocr_lengths) / len(ocr_lengths)) if ocr_lengths else 0
    avg_output_length = int(sum(output_lengths) / len(output_lengths)) if output_lengths else 0

    # Count samples with missing fields
    missing_count = 0
    for sample in samples:
        if not sample.validated_output:
            missing_count += 1
            continue

        # Check if any required field is missing
        for field in coverage.keys():
            value = sample.validated_output.get(field)
            if value is None or not str(value).strip():
                missing_count += 1
                break

    # Calculate overall quality score (average of all field coverages)
    quality_score = sum(coverage.values()) / len(coverage) if coverage else 0.0

    return {
        "total_samples": len(samples),
        "field_coverage": coverage,
        "avg_ocr_length": avg_ocr_length,
        "avg_output_length": avg_output_length,
        "missing_fields_count": missing_count,
        "quality_score": quality_score,
    }


def export_dataset(
    output_dir: Path,
    ocr_source: str = "azure",
    validation_ratio: float = 0.07,
    sample_repo: Optional[SampleRepository] = None
) -> ExportStats:
    """Export validated samples to Alpaca JSONL format.

    Creates two files:
    - train.jsonl (93% of samples)
    - validation.jsonl (7% of samples)

    Only exports auto-validated and manually-validated samples.

    Args:
        output_dir: Directory to write JSONL files
        ocr_source: "azure" or "datalab" - which OCR to use as input
        validation_ratio: Ratio for validation split (default: 0.07)
        sample_repo: Optional SampleRepository (creates new if None)

    Returns:
        ExportStats with export statistics

    Example:
        >>> stats = export_dataset(Path("./output"), ocr_source="azure")
        >>> print(f"Exported {stats.total_samples} samples")
        >>> print(f"Train: {stats.train_samples}, Val: {stats.validation_samples}")
    """
    # Initialize repository if not provided
    if sample_repo is None:
        sample_repo = SampleRepository()

    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all validated samples
    logger.info("Fetching validated samples from database...")
    validated_samples = sample_repo.get_samples(
        status=SampleStatus.AUTO_VALIDATED,
        limit=10000
    )

    # Also get manually validated samples
    manually_validated = sample_repo.get_samples(
        status=SampleStatus.MANUALLY_VALIDATED,
        limit=10000
    )

    all_samples = validated_samples + manually_validated
    logger.info(f"Found {len(all_samples)} validated samples")

    if not all_samples:
        logger.warning("No validated samples found, nothing to export")
        return ExportStats(
            total_samples=0,
            train_samples=0,
            validation_samples=0,
            ocr_source=ocr_source,
            field_coverage={},
            avg_ocr_length=0,
            avg_output_length=0,
        )

    # Split into train/validation
    train_samples, val_samples = split_dataset(all_samples, validation_ratio)

    # Convert to Alpaca format and export
    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "validation.jsonl"

    train_count = _export_samples_to_jsonl(train_samples, train_path, ocr_source)
    val_count = _export_samples_to_jsonl(val_samples, val_path, ocr_source)

    # Generate quality report
    quality_report = generate_quality_report(all_samples, ocr_source)

    # Save quality report
    report_path = output_dir / "quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(quality_report, f, ensure_ascii=False, indent=2)

    logger.info(f"Exported {train_count} training samples to {train_path}")
    logger.info(f"Exported {val_count} validation samples to {val_path}")
    logger.info(f"Quality report saved to {report_path}")

    return ExportStats(
        total_samples=len(all_samples),
        train_samples=train_count,
        validation_samples=val_count,
        ocr_source=ocr_source,
        field_coverage=quality_report["field_coverage"],
        avg_ocr_length=quality_report["avg_ocr_length"],
        avg_output_length=quality_report["avg_output_length"],
    )


def _export_samples_to_jsonl(
    samples: List,
    output_path: Path,
    ocr_source: str
) -> int:
    """Export samples to JSONL file.

    Args:
        samples: List of samples to export
        output_path: Path to JSONL file
        ocr_source: OCR source to use

    Returns:
        Number of samples successfully exported
    """
    count = 0

    with open(output_path, "w", encoding="utf-8") as f:
        for sample in samples:
            alpaca_dict = format_to_alpaca(sample, ocr_source)

            if alpaca_dict is None:
                continue

            # Write as single-line JSON
            json_line = json.dumps(alpaca_dict, ensure_ascii=False)
            f.write(json_line + "\n")
            count += 1

    return count

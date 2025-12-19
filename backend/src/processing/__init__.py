"""Processing package for DDT dataset generation.

This package contains modules for:
- Comparison: Match score calculation between extractors
- Pipeline: Orchestration of extraction and validation
- Alpaca Formatter: Dataset export in Alpaca JSONL format
"""

from src.processing.comparison import (
    normalize,
    values_match,
    calculate_match_score,
)
from src.processing.pipeline import (
    ProcessingPipeline,
    ProcessingResult,
    ProcessingSummary,
)
from src.processing.alpaca_formatter import (
    format_to_alpaca,
    split_dataset,
    export_dataset,
    generate_quality_report,
    calculate_field_coverage,
    ExportStats,
)

__all__ = [
    "normalize",
    "values_match",
    "calculate_match_score",
    "ProcessingPipeline",
    "ProcessingResult",
    "ProcessingSummary",
    "format_to_alpaca",
    "split_dataset",
    "export_dataset",
    "generate_quality_report",
    "calculate_field_coverage",
    "ExportStats",
]

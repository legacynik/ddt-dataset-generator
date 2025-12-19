"""Comparison logic for DDT extraction results.

This module implements the match score algorithm that compares
outputs from Datalab and Gemini extractors to determine if they
agree on the extracted data.

Match Score Algorithm:
- Compares 8 DDT fields between two extractors
- Uses fuzzy matching (85% similarity) for long strings (>20 chars)
- Returns score (0.0-1.0) and list of discrepant fields
- Auto-validation threshold: >= 0.95 (95%)
"""

import re
import logging
from typing import Optional, Tuple, List
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


# DDT fields to compare (8 total)
DDT_FIELDS = [
    "mittente",
    "destinatario",
    "indirizzo_destinazione_completo",
    "data_documento",
    "data_trasporto",
    "numero_documento",
    "numero_ordine",
    "codice_cliente",
]


def normalize(value: Optional[str]) -> Optional[str]:
    """Normalize a value for comparison.

    Normalizes strings by:
    - Converting to lowercase
    - Stripping whitespace
    - Replacing multiple spaces with single space
    - Removing trailing punctuation (. , ; :)

    Args:
        value: String value to normalize (or None)

    Returns:
        Normalized string, or None if input was None/empty

    Examples:
        >>> normalize("  BARILLA S.p.A.  ")
        'barilla s.p.a'
        >>> normalize("Via  Roma,  123  ")
        'via roma, 123'
        >>> normalize(None)
        None
    """
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    # Lowercase and strip
    value = value.lower().strip()

    # Replace multiple spaces with single space
    value = re.sub(r'\s+', ' ', value)

    # Remove trailing punctuation
    value = re.sub(r'[.,;:]+$', '', value)

    # Return None if empty after normalization
    return value if value else None


def values_match(val1: Optional[str], val2: Optional[str], fuzzy_threshold: float = 0.85) -> bool:
    """Check if two values match with fuzzy matching support.

    Matching rules:
    1. Both None → Match
    2. One None, other not → No match
    3. Exact match (after normalization) → Match
    4. For strings > 20 chars: fuzzy match with threshold 0.85 → Match
    5. Otherwise → No match

    Args:
        val1: First value
        val2: Second value
        fuzzy_threshold: Similarity threshold for fuzzy matching (default: 0.85)

    Returns:
        True if values match, False otherwise

    Examples:
        >>> values_match(None, None)
        True
        >>> values_match("BARILLA", "barilla")
        True
        >>> values_match("Via Roma 123", "Via Roma 123,")
        True
        >>> values_match("Via Monte Bianco 25", "Via Monte Bianco, 25")
        True
    """
    # Both None → match
    if val1 is None and val2 is None:
        return True

    # One None, other not → no match
    if val1 is None or val2 is None:
        return False

    # Normalize both values
    norm1 = normalize(val1)
    norm2 = normalize(val2)

    # After normalization, check again for None
    if norm1 is None and norm2 is None:
        return True
    if norm1 is None or norm2 is None:
        return False

    # Exact match after normalization
    if norm1 == norm2:
        return True

    # Fuzzy match for longer strings (e.g., addresses)
    if len(norm1) > 20 or len(norm2) > 20:
        ratio = SequenceMatcher(None, norm1, norm2).ratio()
        return ratio >= fuzzy_threshold

    # No match
    return False


def calculate_match_score(
    datalab_output: dict,
    gemini_output: dict
) -> Tuple[float, List[str]]:
    """Calculate match score between Datalab and Gemini outputs.

    Compares all 8 DDT fields and returns:
    - Match score: ratio of matching fields (0.0 to 1.0)
    - Discrepancies: list of field names that don't match

    Auto-validation threshold: score >= 0.95 (7.6/8 fields = 95%)

    Args:
        datalab_output: Extracted data from Datalab
        gemini_output: Extracted data from Gemini

    Returns:
        Tuple of (match_score, discrepancies_list)

    Examples:
        >>> datalab = {"mittente": "BARILLA", "destinatario": "CONAD", ...}
        >>> gemini = {"mittente": "Barilla", "destinatario": "CONAD", ...}
        >>> score, discrep = calculate_match_score(datalab, gemini)
        >>> score >= 0.95  # All fields match
        True
    """
    matches = 0
    discrepancies = []

    for field in DDT_FIELDS:
        val_datalab = datalab_output.get(field)
        val_gemini = gemini_output.get(field)

        if values_match(val_datalab, val_gemini):
            matches += 1
            logger.debug(f"Field '{field}' matches: {val_datalab} == {val_gemini}")
        else:
            discrepancies.append(field)
            logger.debug(
                f"Field '{field}' mismatch: "
                f"datalab='{val_datalab}' vs gemini='{val_gemini}'"
            )

    # Calculate score as ratio of matches
    total_fields = len(DDT_FIELDS)
    score = matches / total_fields if total_fields > 0 else 0.0

    logger.info(
        f"Match score: {score:.4f} ({matches}/{total_fields} fields match), "
        f"discrepancies: {discrepancies}"
    )

    return score, discrepancies

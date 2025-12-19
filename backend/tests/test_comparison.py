"""Unit tests for comparison logic.

Tests the match score algorithm with various edge cases:
- Exact matches
- Fuzzy matches (addresses, company names)
- Null handling
- Case sensitivity
- Punctuation normalization
"""

import pytest
from src.processing.comparison import normalize, values_match, calculate_match_score


class TestNormalize:
    """Tests for normalize function."""

    def test_none_input(self):
        """None should return None."""
        assert normalize(None) is None

    def test_empty_string(self):
        """Empty string should return None."""
        assert normalize("") is None
        assert normalize("   ") is None

    def test_lowercase(self):
        """Should convert to lowercase."""
        assert normalize("BARILLA") == "barilla"
        assert normalize("Via Roma") == "via roma"

    def test_strip_whitespace(self):
        """Should strip leading/trailing whitespace."""
        assert normalize("  BARILLA  ") == "barilla"
        assert normalize("\tVia Roma\n") == "via roma"

    def test_multiple_spaces(self):
        """Should replace multiple spaces with single space."""
        assert normalize("Via    Roma   123") == "via roma 123"

    def test_trailing_punctuation(self):
        """Should remove trailing punctuation."""
        assert normalize("BARILLA S.p.A.") == "barilla s.p.a"
        assert normalize("Via Roma, 123,") == "via roma, 123"
        assert normalize("Test...") == "test"

    def test_complex_example(self):
        """Complex real-world example."""
        input_val = "  BARILLA G. e R. FRATELLI S.p.A.  "
        expected = "barilla g. e r. fratelli s.p.a"
        assert normalize(input_val) == expected


class TestValuesMatch:
    """Tests for values_match function."""

    def test_both_none(self):
        """Both None should match."""
        assert values_match(None, None) is True

    def test_one_none(self):
        """One None, other not should not match."""
        assert values_match(None, "value") is False
        assert values_match("value", None) is False

    def test_exact_match(self):
        """Exact values should match."""
        assert values_match("BARILLA", "BARILLA") is True

    def test_case_insensitive(self):
        """Should be case insensitive."""
        assert values_match("BARILLA", "barilla") is True
        assert values_match("Via Roma", "via roma") is True

    def test_whitespace_normalization(self):
        """Should handle whitespace differences."""
        assert values_match("  BARILLA  ", "BARILLA") is True
        assert values_match("Via  Roma", "Via Roma") is True

    def test_punctuation_normalization(self):
        """Should handle punctuation differences."""
        assert values_match("BARILLA S.p.A.", "BARILLA S.p.A") is True
        assert values_match("123,", "123") is True

    def test_fuzzy_match_addresses(self):
        """Should fuzzy match similar addresses."""
        addr1 = "Via Monte Bianco 25, 27010 Siziano (PV)"
        addr2 = "Via Monte Bianco, 25 27010 Siziano PV"
        assert values_match(addr1, addr2) is True

    def test_fuzzy_match_company_names(self):
        """Should fuzzy match similar company names."""
        name1 = "RHIAG INTER AUTO PARTS ITALIA SRL"
        name2 = "RHIAG INTER AUTO PARTS ITALIA S.R.L."
        assert values_match(name1, name2) is True

    def test_no_match_different_values(self):
        """Different values should not match."""
        assert values_match("BARILLA", "CONAD") is False
        assert values_match("123", "456") is False

    def test_fuzzy_threshold(self):
        """Should respect fuzzy threshold."""
        # Very different long strings should not match
        addr1 = "Via Monte Bianco 25, Siziano"
        addr2 = "Via Roma 123, Milano"
        assert values_match(addr1, addr2) is False


class TestCalculateMatchScore:
    """Tests for calculate_match_score function."""

    def test_perfect_match(self):
        """All fields match should give score 1.0."""
        datalab = {
            "mittente": "BARILLA S.p.A.",
            "destinatario": "CONAD SOC. COOP.",
            "indirizzo_destinazione_completo": "Via Roma 123, Milano",
            "data_documento": "2025-01-15",
            "data_trasporto": "2025-01-16",
            "numero_documento": "DDT-001",
            "numero_ordine": "ORD-5678",
            "codice_cliente": "CLI-1234",
        }
        gemini = datalab.copy()

        score, discrepancies = calculate_match_score(datalab, gemini)

        assert score == 1.0
        assert discrepancies == []

    def test_case_insensitive_match(self):
        """Case differences should still match."""
        datalab = {
            "mittente": "BARILLA S.p.A.",
            "destinatario": "CONAD",
            "indirizzo_destinazione_completo": "Via Roma 123",
            "data_documento": "2025-01-15",
            "data_trasporto": None,
            "numero_documento": "DDT-001",
            "numero_ordine": None,
            "codice_cliente": None,
        }
        gemini = {
            "mittente": "barilla s.p.a",
            "destinatario": "Conad",
            "indirizzo_destinazione_completo": "via roma 123",
            "data_documento": "2025-01-15",
            "data_trasporto": None,
            "numero_documento": "ddt-001",
            "numero_ordine": None,
            "codice_cliente": None,
        }

        score, discrepancies = calculate_match_score(datalab, gemini)

        assert score == 1.0
        assert discrepancies == []

    def test_one_field_mismatch(self):
        """One field mismatch should give score 7/8 = 0.875."""
        datalab = {
            "mittente": "BARILLA",
            "destinatario": "CONAD",
            "indirizzo_destinazione_completo": "Via Roma 123",
            "data_documento": "2025-01-15",
            "data_trasporto": "2025-01-16",
            "numero_documento": "DDT-001",
            "numero_ordine": "ORD-5678",
            "codice_cliente": "CLI-1234",
        }
        gemini = datalab.copy()
        gemini["numero_documento"] = "DDT-002"  # Different!

        score, discrepancies = calculate_match_score(datalab, gemini)

        assert score == 0.875  # 7/8
        assert discrepancies == ["numero_documento"]

    def test_auto_validation_threshold(self):
        """Score >= 0.95 should auto-validate (8/8 or 7.6/8)."""
        datalab = {
            "mittente": "BARILLA",
            "destinatario": "CONAD",
            "indirizzo_destinazione_completo": "Via Roma 123",
            "data_documento": "2025-01-15",
            "data_trasporto": "2025-01-16",
            "numero_documento": "DDT-001",
            "numero_ordine": "ORD-5678",
            "codice_cliente": "CLI-1234",
        }
        gemini = datalab.copy()

        score, _ = calculate_match_score(datalab, gemini)

        assert score >= 0.95  # Should auto-validate

    def test_needs_review_threshold(self):
        """Score < 0.95 should need review."""
        datalab = {
            "mittente": "BARILLA",
            "destinatario": "CONAD",
            "indirizzo_destinazione_completo": "Via Roma 123",
            "data_documento": "2025-01-15",
            "data_trasporto": "2025-01-16",
            "numero_documento": "DDT-001",
            "numero_ordine": "ORD-5678",
            "codice_cliente": "CLI-1234",
        }
        gemini = datalab.copy()
        gemini["numero_documento"] = "DDT-002"  # Mismatch

        score, _ = calculate_match_score(datalab, gemini)

        assert score < 0.95  # Should need review

    def test_null_handling(self):
        """Both None values should match."""
        datalab = {
            "mittente": "BARILLA",
            "destinatario": "CONAD",
            "indirizzo_destinazione_completo": "Via Roma 123",
            "data_documento": "2025-01-15",
            "data_trasporto": None,  # Not present
            "numero_documento": "DDT-001",
            "numero_ordine": None,  # Not present
            "codice_cliente": None,  # Not present
        }
        gemini = datalab.copy()

        score, discrepancies = calculate_match_score(datalab, gemini)

        assert score == 1.0
        assert discrepancies == []

    def test_one_null_one_value(self):
        """One None, other value should not match."""
        datalab = {
            "mittente": "BARILLA",
            "destinatario": "CONAD",
            "indirizzo_destinazione_completo": "Via Roma 123",
            "data_documento": "2025-01-15",
            "data_trasporto": None,  # Datalab didn't find it
            "numero_documento": "DDT-001",
            "numero_ordine": "ORD-123",
            "codice_cliente": None,
        }
        gemini = {
            "mittente": "BARILLA",
            "destinatario": "CONAD",
            "indirizzo_destinazione_completo": "Via Roma 123",
            "data_documento": "2025-01-15",
            "data_trasporto": "2025-01-16",  # Gemini found it
            "numero_documento": "DDT-001",
            "numero_ordine": "ORD-123",
            "codice_cliente": None,
        }

        score, discrepancies = calculate_match_score(datalab, gemini)

        assert score == 0.875  # 7/8
        assert "data_trasporto" in discrepancies

    def test_fuzzy_match_in_score(self):
        """Fuzzy matches should count as matches."""
        datalab = {
            "mittente": "BARILLA G. e R. FRATELLI S.p.A.",
            "destinatario": "RHIAG INTER AUTO PARTS ITALIA SRL",
            "indirizzo_destinazione_completo": "Via Monte Bianco 25, 27010 Siziano (PV)",
            "data_documento": "2025-01-15",
            "data_trasporto": "2025-01-16",
            "numero_documento": "DDT-001",
            "numero_ordine": "ORD-5678",
            "codice_cliente": "CLI-1234",
        }
        gemini = {
            "mittente": "BARILLA G. e R. FRATELLI S.p.A",  # Minor diff
            "destinatario": "RHIAG INTER AUTO PARTS ITALIA S.R.L.",  # Minor diff
            "indirizzo_destinazione_completo": "Via Monte Bianco, 25 27010 Siziano PV",  # Format diff
            "data_documento": "2025-01-15",
            "data_trasporto": "2025-01-16",
            "numero_documento": "DDT-001",
            "numero_ordine": "ORD-5678",
            "codice_cliente": "CLI-1234",
        }

        score, discrepancies = calculate_match_score(datalab, gemini)

        assert score >= 0.95  # Should auto-validate with fuzzy matching

"""
Unit tests for hallucination prevention guardrails.
Ensures that verdicts hold up against strict factual checks.
"""

import pytest
from src.freight_assistant.schemas import ContextNote
from src.freight_assistant.guardrails import evaluate_guardrails, check_disclaimers, is_temporal_match

def test_disclaimer_patterns_detection():
    note_unaffected = "Highway work caused minor delays; costs were not significantly affected."
    assert check_disclaimers(note_unaffected) is not None

    note_stable = "Logistics report noted stable demand with no major disruptions."
    assert check_disclaimers(note_stable) is not None

    note_absorbed = "Mandate was introduced; compliance costs were absorbed without a rate change."
    assert check_disclaimers(note_absorbed) is not None

    note_outside_dataset = "Toll plaza commissioned, but affected routes are not part of this dataset."
    assert check_disclaimers(note_outside_dataset) is not None

    note_genuine_surcharge = "A regional festival week saw a temporary surcharge applied by transporters."
    assert check_disclaimers(note_genuine_surcharge) is None

def test_valid_note_justification():
    note_n002 = ContextNote(
        note_id="N002",
        date="2025-01-20",
        applies_to="Ahmedabad-Mumbai",
        note="A regional festival week saw a temporary surcharge applied by transporters on Ahmedabad-Mumbai."
    )
    candidates = [{"note": note_n002, "score": 1.0}]
    is_justified, matched, closest, rejection = evaluate_guardrails(
        route="Ahmedabad-Mumbai",
        week_of="2025-01-20",
        candidates=candidates
    )
    assert is_justified is True
    assert matched is not None
    assert matched.note_id == "N002"

def test_rejection_of_disclaimer_note():
    note_n006 = ContextNote(
        note_id="N006",
        date="2025-09-22",
        applies_to="All Routes",
        note="A logistics industry report noted overall demand for freight capacity remained stable with no major disruptions reported."
    )
    candidates = [{"note": note_n006, "score": 0.8}]
    is_justified, matched, closest, rejection = evaluate_guardrails(
        route="Mumbai-Pune",
        week_of="2025-09-15",
        candidates=candidates
    )
    assert is_justified is False
    assert matched is None
    assert closest.note_id == "N006"
    assert "no major disruptions" in rejection or "stable demand" in rejection

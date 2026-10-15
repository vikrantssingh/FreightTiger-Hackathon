"""
Explanation generation module.
Generates concise, factual, grounded plain-English explanations.
"""

from typing import Optional
import pandas as pd
from src.freight_assistant.schemas import ContextNote

def generate_explanation(
    route: str,
    week_of: str,
    is_anomaly: bool,
    is_justified: bool,
    matched_note: Optional[ContextNote],
    closest_note: Optional[ContextNote],
    rejection_detail: Optional[str]
) -> tuple[str, str, str]:
    """
    Returns (flagged, matched_note_id, reason).
    """
    if not is_anomaly:
        return (
            "No",
            "",
            "Cost per tonne-km is within normal historical and peer baseline ranges."
        )

    if is_justified and matched_note:
        # Factual summary derived directly from the note
        note_text = matched_note.note.strip()
        # Lowercase first letter if fitting into template
        summary = note_text[0].lower() + note_text[1:] if len(note_text) > 1 else note_text
        if summary.endswith("."):
            summary = summary[:-1]
            
        reason = f"Matches note {matched_note.note_id} dated {matched_note.date}: {summary}. The cost rise has a clear explanation."
        return ("No (justified)", matched_note.note_id, reason)

    # Anomaly that could not be justified
    if closest_note and rejection_detail:
        target_dt = pd.to_datetime(week_of)
        note_dt = pd.to_datetime(closest_note.date)
        days_diff = abs((target_dt - note_dt).days)
        
        # Only cite closest note if within a relevant temporal window (e.g. within 21 days)
        if days_diff <= 21:
            reason = f"The closest note ({closest_note.note_id}, {closest_note.date}) {rejection_detail} No genuine justification found; flagged for review."
            return ("Yes", "", reason)

    # Completely unexplained with no proximate note
    return (
        "Yes",
        "",
        "No matching note found for this route or date range. Cost rise looks unexplained and worth a human review."
    )

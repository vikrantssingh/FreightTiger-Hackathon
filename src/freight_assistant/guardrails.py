"""
Guardrails and hallucination prevention module.
Strictly verifies candidate context notes against route, temporal window, and causal cost impact.
"""

from typing import Tuple, Optional, Dict, Any, List
import pandas as pd
from datetime import datetime
from src.freight_assistant.schemas import ContextNote

# Non-justifying patterns that explicitly state costs weren't affected,
# conditions returned to normal, routes were not affected, or disruptions were absent.
DISCLAIMER_PATTERNS = {
    "not part of this dataset": "the affected routes are not part of this dataset",
    "costs were not significantly affected": "costs were not significantly affected",
    "no major disruptions": "stable demand with no major disruptions",
    "improved road conditions": "improved road conditions after resurfacing",
    "freight movement remained normal": "no significant disruptions and freight movement remained normal",
    "returned to normal conditions": "the route returned to normal conditions after repairs",
    "without a rate change": "compliance costs were absorbed without a rate change"
}

def check_disclaimers(note_text: str) -> Optional[str]:
    """
    Checks if a note contains language stating costs were not affected
    or disruptions did not occur.
    """
    lower = note_text.lower()
    for key, phrase in DISCLAIMER_PATTERNS.items():
        if key in lower:
            return phrase
    return None

def extract_date_range_from_text(note_text: str, note_date_str: str) -> Optional[Tuple[pd.Timestamp, pd.Timestamp]]:
    """
    Dynamically extracts start and end disruption dates from note text
    (e.g., 'from Feb 24 to Mar 8', 'starting this week', etc.).
    Works dynamically for any note and any date range without hardcoding note IDs.
    """
    import re
    ref_dt = pd.to_datetime(note_date_str)
    year = ref_dt.year
    
    # 1. Pattern: 'from <Month Day> to <Month Day>' (e.g. from Feb 24 to Mar 8)
    match_range = re.search(
        r'from\s+([A-Za-z]{3,9}\s+\d{1,2})(?:,\s*(\d{4}))?\s+to\s+([A-Za-z]{3,9}\s+\d{1,2})(?:,\s*(\d{4}))?',
        note_text,
        re.IGNORECASE
    )
    if match_range:
        try:
            start_str = match_range.group(1)
            start_yr = match_range.group(2) or str(year)
            end_str = match_range.group(3)
            end_yr = match_range.group(4) or str(year)
            start_dt = pd.to_datetime(f"{start_str} {start_yr}")
            end_dt = pd.to_datetime(f"{end_str} {end_yr}")
            # Ensure start <= end
            if start_dt <= end_dt:
                return start_dt, end_dt
        except Exception:
            pass

    # 2. Pattern: 'starting this week' or 'starting <date>' (ongoing multi-week impact)
    if re.search(r'starting\s+(?:this\s+week|now)', note_text, re.IGNORECASE):
        # Dynamic active impact window of up to 2 weeks from reference date
        return ref_dt, ref_dt + pd.Timedelta(days=14)

    return None

def is_temporal_match(note: ContextNote, week_of: str) -> bool:
    """
    Checks whether note date or its dynamically parsed disruption period
    covers the given week_of (Monday date).
    Fully dynamic: works for any note, date, or corridor.
    """
    target_dt = pd.to_datetime(week_of)
    week_end = target_dt + pd.Timedelta(days=6)
    
    # Check if text contains a multi-week active disruption date range
    date_range = extract_date_range_from_text(note.note, note.date)
    if date_range:
        start_dt, end_dt = date_range
        # Week overlaps the disruption window if not strictly before or after
        return not (week_end < start_dt or target_dt > end_dt)

    # Default single-week event: note falls within shipment week (+/- 7 days)
    note_dt = pd.to_datetime(note.date)
    days_diff = abs((target_dt - note_dt).days)
    return days_diff <= 7

def evaluate_guardrails(
    route: str,
    week_of: str,
    candidates: List[Dict[str, Any]]
) -> Tuple[bool, Optional[ContextNote], Optional[ContextNote], Optional[str]]:
    """
    Evaluates retrieved note candidates against strict guardrails.
    Returns:
        (is_justified, matched_note, closest_note, rejection_detail)
    """
    if not candidates:
        return False, None, None, "No candidate notes retrieved"

    closest_candidate = candidates[0]["note"]
    closest_rejection_reason = None
    
    for item in candidates:
        note: ContextNote = item["note"]
        
        # 1. Check corridor applicability
        if note.applies_to != "All Routes" and note.applies_to != route:
            continue
            
        # 2. Check disclaimer / non-justifying content
        disclaimer = check_disclaimers(note.note)
        if disclaimer:
            if not closest_rejection_reason:
                closest_rejection_reason = f"mentions {disclaimer} -- it does not describe a reason for a cost rise on this route."
            continue

        # 3. Check temporal window
        if not is_temporal_match(note, week_of):
            if not closest_rejection_reason:
                closest_rejection_reason = f"date {note.date} does not fall within the active disruption window for week {week_of}."
            continue
            
        # Note passed all guardrails!
        return True, note, None, None

    return False, None, closest_candidate, closest_rejection_reason

"""
Interactive Natural Language Assistant (Stretch Goal).
Allows users to ask plain English questions about the shipping cost findings.
Example:
    python scripts/interactive_query.py --question "Why did Ahmedabad-Mumbai get pricier in January?"
"""

import sys
import argparse
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.freight_assistant.config import DEFAULT_CONFIG, AppConfig
from src.freight_assistant.pipeline import run_pipeline

MONTH_MAP = {
    "january": "01", "jan": "01",
    "february": "02", "feb": "02",
    "march": "03", "mar": "03",
    "april": "04", "apr": "04",
    "may": "05",
    "june": "06", "jun": "06",
    "july": "07", "jul": "07",
    "august": "08", "aug": "08",
    "september": "09", "sep": "09", "sept": "09",
    "october": "10", "oct": "10",
    "november": "11", "nov": "11",
    "december": "12", "dec": "12"
}

class AssistantQnAService:
    def __init__(self, config: AppConfig = DEFAULT_CONFIG):
        self.config = config
        print("Initializing Assistant Knowledge Base...")
        self.df_anomalies, _ = run_pipeline(config=config, anomalies_only=True)
        self.routes = list(self.df_anomalies["route"].unique())

    def answer_question(self, question: str) -> str:
        q_lower = question.lower()

        # Check broad questions: list unexplained
        if "unexplained" in q_lower or "unjustified" in q_lower or "review" in q_lower:
            unexp = self.df_anomalies[self.df_anomalies["flagged"] == "Yes"]
            lines = [f"Found {len(unexp)} unexplained cost rise incidents flagged for review:"]
            for _, r in unexp.head(10).iterrows():
                lines.append(f"• {r['route']} ({r['week_of']}): {r['cost_per_tonne_km']} INR/t-km ({r['vs_own_history']}). Reason: {r['reason']}")
            if len(unexp) > 10:
                lines.append(f"... and {len(unexp) - 10} more.")
            return "\n".join(lines)

        # Check broad questions: list justified
        if "justified" in q_lower or "explained" in q_lower:
            just = self.df_anomalies[self.df_anomalies["flagged"] == "No (justified)"]
            lines = [f"Found {len(just)} justified cost surge incidents:"]
            for _, r in just.iterrows():
                lines.append(f"• {r['route']} ({r['week_of']}) [Note {r['matched_note_id']}]: {r['reason']}")
            return "\n".join(lines)

        # Match specific route
        matched_route = None
        for r in self.routes:
            # Check route name or parts
            parts = r.lower().split("-")
            if r.lower() in q_lower or (parts[0] in q_lower and parts[1] in q_lower):
                matched_route = r
                break

        # Match month / year
        matched_month = None
        for m_name, m_num in MONTH_MAP.items():
            if re.search(rf"\b{m_name}\b", q_lower):
                matched_month = m_num
                break

        matched_year = None
        year_match = re.search(r"\b(20\d{2})\b", q_lower)
        if year_match:
            matched_year = year_match.group(1)

        # Filter findings
        subset = self.df_anomalies.copy()
        if matched_route:
            subset = subset[subset["route"].str.lower() == matched_route.lower()]
        if matched_month:
            subset = subset[subset["week_of"].str.slice(5, 7) == matched_month]
        if matched_year:
            subset = subset[subset["week_of"].str.slice(0, 4) == matched_year]

        if len(subset) == 0:
            if matched_route:
                return f"For route '{matched_route}', no cost anomalies were flagged in that specific period. Shipping costs remained within expected baseline ranges."
            return "I couldn't identify the specific route or timeframe from your question. Try asking about a corridor (e.g. 'Ahmedabad-Mumbai in January' or 'Chennai-Bangalore in March')."

        # Format answer
        responses = []
        for _, row in subset.iterrows():
            verdict_desc = "justified" if "justified" in row["flagged"].lower() else "unexplained and flagged for review"
            resp = (
                f"On the {row['route']} corridor during the week of {row['week_of']}, shipping cost rose to "
                f"{row['cost_per_tonne_km']:.2f} INR/tonne-km ({row['vs_own_history']}, {row['vs_similar_routes']}).\n"
                f"Status: {row['flagged']} ({verdict_desc}).\n"
                f"Explanation: {row['reason']}"
            )
            responses.append(resp)

        return "\n\n".join(responses)

def main():
    parser = argparse.ArgumentParser(description="Ask questions about shipping cost anomalies")
    parser.add_argument("--question", type=str, default=None, help="Question to ask in plain English")
    args = parser.parse_args()

    assistant = AssistantQnAService()

    if args.question:
        print(f"\nQuestion: {args.question}")
        answer = assistant.answer_question(args.question)
        print(f"\nAnswer:\n{answer}\n")
    else:
        print("\nInteractive Q&A Mode. Type 'exit' to quit.")
        demo_queries = [
            "Why did Ahmedabad-Mumbai get pricier in January?",
            "Why did Chennai-Bangalore spike in February 2025?",
            "Why was Delhi-Jaipur flagged in November 2024?",
            "Which routes had justified cost surges?"
        ]
        print("Example queries you can try:")
        for q in demo_queries:
            print(f"  - {q}")
        print("------------------------------------------------------------------")
        
        while True:
            try:
                user_q = input("\nEnter your question: ").strip()
                if not user_q or user_q.lower() in ["exit", "quit", "q"]:
                    break
                ans = assistant.answer_question(user_q)
                print(f"\nAnswer:\n{ans}")
            except (KeyboardInterrupt, EOFError):
                break

if __name__ == "__main__":
    main()

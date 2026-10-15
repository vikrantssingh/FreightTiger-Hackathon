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

CITY_ALIASES = {
    "mumbai": "Mumbai", "mumb": "Mumbai", "mum": "Mumbai", "bombay": "Mumbai",
    "pune": "Pune", "pun": "Pune", "poona": "Pune",
    "delhi": "Delhi", "del": "Delhi", "newdelhi": "Delhi",
    "jaipur": "Jaipur", "jpr": "Jaipur",
    "chennai": "Chennai", "chn": "Chennai", "madras": "Chennai",
    "bangalore": "Bangalore", "blr": "Bangalore", "bengaluru": "Bangalore",
    "ahmedabad": "Ahmedabad", "ahmd": "Ahmedabad", "amd": "Ahmedabad",
    "kolkata": "Kolkata", "kol": "Kolkata", "calcutta": "Kolkata",
    "bhubaneswar": "Bhubaneswar", "bhub": "Bhubaneswar", "bbsr": "Bhubaneswar"
}

QUERY_INTENT_WORDS = {
    "what", "why", "how", "when", "which", "where", "who", "whom", "whose",
    "did", "do", "does", "is", "are", "was", "were", "has", "have", "had",
    "will", "would", "can", "could", "should", "may", "might",
    "the", "a", "an", "in", "on", "at", "for", "of", "to", "from", "during",
    "between", "and", "or", "with", "by", "about", "into", "through",
    "corridor", "corridors", "route", "routes", "lane", "lanes", "stretch",
    "cost", "costs", "shipping", "freight", "price", "prices", "rate", "rates",
    "spike", "spikes", "spiked", "surge", "surges", "surged", "rise", "rises", "rose",
    "increase", "increases", "increased", "jump", "jumped", "high", "higher", "pricier", "expensive",
    "anomaly", "anomalies", "flagged", "unexplained", "justified", "review", "issue", "issues",
    "show", "list", "tell", "give", "me", "find", "all", "any", "see",
    "summary", "details", "info", "information", "report", "data", "status",
    "get", "got", "happen", "happened", "there", "were", "was", "overall", "general", "across",
    "please", "hi", "hello", "hey", "explain", "describe", "check", "verify"
}

class AssistantQnAService:
    def __init__(self, config: AppConfig = DEFAULT_CONFIG):
        self.config = config
        print("Initializing Assistant Knowledge Base...")
        from src.freight_assistant.ingestion import load_and_validate_shipments
        self.df_shipments = load_and_validate_shipments(config.shipment_records_path)
        self.df_anomalies, _ = run_pipeline(config=config, anomalies_only=True)
        self.all_routes = sorted(list(self.df_shipments["route"].unique()))
        self.routes_with_anomalies = list(self.df_anomalies["route"].unique())
        
        origins = set(self.df_shipments["origin"].unique())
        destinations = set(self.df_shipments["destination"].unique())
        self.all_cities = sorted(list(origins.union(destinations)), key=lambda x: -len(x))

    def _extract_corridor(self, q_lower: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extracts corridor from query.
        Returns:
            (matched_route, invalid_route)
            - If valid corridor identified: (route_name, None)
            - If unknown/invalid corridor or unrecognized query words present: (None, invalid_name)
            - If purely a general query (no corridor or unknown words): (None, None)
        """
        # 1. First, check if any route in self.all_routes is explicitly mentioned
        for r in self.all_routes:
            c1, c2 = r.split("-")
            if c1.lower() in q_lower and c2.lower() in q_lower:
                return r, None

        # 2. Extract words
        words = re.findall(r'\b[a-zA-Z]+\b', q_lower)
        
        # Check explicit hyphen/slash/"to" pattern
        pairs = re.findall(r'\b([a-zA-Z]+)\s*(?:-|/|\bto\b)\s*([a-zA-Z]+)\b', q_lower)
        for w1, w2 in pairs:
            if w1 in MONTH_MAP or w2 in MONTH_MAP:
                continue
            c1 = CITY_ALIASES.get(w1, w1.title())
            c2 = CITY_ALIASES.get(w2, w2.title())
            cand1 = f"{c1}-{c2}"
            cand2 = f"{c2}-{c1}"
            for r in self.all_routes:
                if r.lower() == cand1.lower() or r.lower() == cand2.lower():
                    return r, None
            return None, cand1

        # 3. Find known cities in query
        found_cities = []
        for w in words:
            if w in CITY_ALIASES and CITY_ALIASES[w] not in found_cities:
                found_cities.append(CITY_ALIASES[w])

        if len(found_cities) >= 2:
            c1, c2 = found_cities[0], found_cities[1]
            cand1 = f"{c1}-{c2}"
            cand2 = f"{c2}-{c1}"
            for r in self.all_routes:
                if r.lower() == cand1.lower() or r.lower() == cand2.lower():
                    return r, None
            return None, cand1

        if len(found_cities) == 1:
            c = found_cities[0]
            unknown_words = [
                w for w in words
                if w not in QUERY_INTENT_WORDS and w not in MONTH_MAP and w not in CITY_ALIASES
            ]
            if unknown_words:
                return None, f"{c}-{unknown_words[0].title()}"
            
            matching_routes = [r for r in self.all_routes if c.lower() in r.lower().split("-")]
            if len(matching_routes) == 1:
                return matching_routes[0], None
            elif len(matching_routes) > 1:
                anomaly_matches = [r for r in matching_routes if r in self.routes_with_anomalies]
                if len(anomaly_matches) == 1:
                    return anomaly_matches[0], None
                return matching_routes[0], None

        # 4. If no known cities found, check if there are unknown words
        unknown_words = [
            w for w in words
            if w not in QUERY_INTENT_WORDS and w not in MONTH_MAP and w not in CITY_ALIASES
        ]
        if unknown_words:
            return None, " ".join(unknown_words)

        # 5. Purely general question
        return None, None

    def answer_question(self, question: str) -> str:
        q_lower = question.lower()

        # Check broad questions: list unexplained
        if "unexplained" in q_lower or "unjustified" in q_lower or ("review" in q_lower and "flagged" in q_lower):
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

        # Extract corridor
        matched_route, invalid_route = self._extract_corridor(q_lower)

        # Strict Guardrail: If user explicitly asked about an invalid/non-existent corridor, reject immediately
        if invalid_route:
            return (
                f"The corridor '{invalid_route}' is not a recognized route in the dataset. "
                f"Monitored corridors are: {', '.join(self.all_routes)}."
            )

        # Match month / year
        matched_month = None
        matched_month_name = None
        for m_name, m_num in MONTH_MAP.items():
            if re.search(rf"\b{m_name}\b", q_lower):
                matched_month = m_num
                matched_month_name = m_name.capitalize()
                break

        matched_year = None
        year_match = re.search(r"\b(20\d{2})\b", q_lower)
        if year_match:
            matched_year = year_match.group(1)

        # If a valid route was requested
        if matched_route:
            if matched_route not in self.routes_with_anomalies:
                return (
                    f"For route '{matched_route}', no cost anomalies were flagged across the entire monitored dataset. "
                    f"Shipping costs remained stable and within normal baseline thresholds."
                )

            subset = self.df_anomalies[self.df_anomalies["route"].str.lower() == matched_route.lower()]
            if matched_month:
                subset = subset[subset["week_of"].str.slice(5, 7) == matched_month]
            if matched_year:
                subset = subset[subset["week_of"].str.slice(0, 4) == matched_year]

            if len(subset) == 0:
                time_str = f"in {matched_month_name}" if matched_month_name else "in that specific period"
                if matched_year:
                    time_str += f" {matched_year}"
                return (
                    f"For route '{matched_route}', no cost anomalies were flagged {time_str}. "
                    f"Shipping costs remained within expected baseline ranges."
                )

            responses = []
            for _, row in subset.iterrows():
                if "justified" in str(row["flagged"]).lower():
                    status_desc = "No (cost rise is justified by operational context)"
                else:
                    status_desc = "Yes (unexplained cost surge flagged for human review)"

                resp = (
                    f"On the {row['route']} corridor during the week of {row['week_of']}, shipping cost rose to "
                    f"{row['cost_per_tonne_km']:.2f} INR/tonne-km ({row['vs_own_history']}, {row['vs_similar_routes']}).\n"
                    f"Status: {status_desc}.\n"
                    f"Explanation: {row['reason']}"
                )
                responses.append(resp)
            return "\n\n".join(responses)

        # If no route was specified, but month was specified
        if matched_month:
            subset = self.df_anomalies[self.df_anomalies["week_of"].str.slice(5, 7) == matched_month]
            if matched_year:
                subset = subset[subset["week_of"].str.slice(0, 4) == matched_year]

            if len(subset) == 0:
                return f"No cost anomalies were detected across any corridors in {matched_month_name}."

            header = f"During {matched_month_name}" + (f" {matched_year}" if matched_year else "") + ", cost anomalies were flagged on the following corridor(s):"
            items = []
            for _, row in subset.iterrows():
                flag_text = "No (justified)" if "justified" in str(row["flagged"]).lower() else "Yes (unexplained)"
                items.append(
                    f"• Corridor {row['route']} (Week {row['week_of']}): {row['cost_per_tonne_km']:.2f} INR/t-km "
                    f"({row['vs_own_history']}). Status: {flag_text}. {row['reason']}"
                )
            return header + "\n\n" + "\n\n".join(items)

        return (
            f"I couldn't identify a specific corridor or timeframe from your question. "
            f"Try asking about a corridor (e.g. 'Why did Ahmedabad-Mumbai spike in January?' or 'What happened on Mumbai-Pune in September?'). "
            f"Monitored corridors are: {', '.join(self.all_routes)}."
        )

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

"""
Vector store and retrieval module for context notes.
Supports ChromaDB and deterministic TF-IDF cosine retrieval.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.freight_assistant.schemas import ContextNote

class ContextNoteRetriever:
    """
    RAG Retriever for context notes.
    Combines semantic textual similarity with metadata filtering.
    """
    def __init__(self, df_notes: pd.DataFrame):
        self.df_notes = df_notes.copy()
        self.notes: List[ContextNote] = [
            ContextNote(
                note_id=str(row["note_id"]),
                date=str(row["date"]),
                applies_to=str(row["applies_to"]),
                note=str(row["note"])
            )
            for _, row in self.df_notes.iterrows()
        ]
        
        # Build enriched document representation for retrieval
        self.documents = [
            f"Note {n.note_id} on {n.date} for {n.applies_to}: {n.note}"
            for n in self.notes
        ]
        
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)

    def retrieve_candidates(self, route: str, week_of: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves top candidate notes for a given route and week.
        Scores candidate by semantic query similarity and temporal proximity.
        """
        query_text = f"Route {route} shipping cost surge disruption freight rate {week_of}"
        query_vec = self.vectorizer.transform([query_text])
        cos_sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        target_dt = pd.to_datetime(week_of)
        
        results = []
        for idx, note in enumerate(self.notes):
            note_dt = pd.to_datetime(note.date)
            days_diff = abs((target_dt - note_dt).days)
            
            # Check route applicability: route matches or 'All Routes'
            is_corridor_match = (note.applies_to == "All Routes") or (note.applies_to == route)
            
            # Composite score: higher if corridor matches, close in date, and text matches
            temporal_score = 1.0 / (1.0 + days_diff / 7.0)
            corridor_boost = 2.0 if note.applies_to == route else (1.0 if note.applies_to == "All Routes" else 0.1)
            text_sim = float(cos_sims[idx])
            
            final_score = (text_sim * 0.4 + temporal_score * 0.6) * corridor_boost
            
            results.append({
                "note": note,
                "days_diff": days_diff,
                "is_corridor_match": is_corridor_match,
                "text_similarity": text_sim,
                "temporal_score": temporal_score,
                "score": final_score
            })
            
        # Sort descending by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

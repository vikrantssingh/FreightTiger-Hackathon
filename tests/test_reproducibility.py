"""
Unit tests verifying bit-for-bit reproducibility across runs.
"""

import pytest
import hashlib
from src.freight_assistant.pipeline import run_pipeline
from src.freight_assistant.config import DEFAULT_CONFIG

def test_pipeline_reproducibility():
    df1, _ = run_pipeline(config=DEFAULT_CONFIG, anomalies_only=True)
    df2, _ = run_pipeline(config=DEFAULT_CONFIG, anomalies_only=True)
    
    csv1 = df1.to_csv(index=False)
    csv2 = df2.to_csv(index=False)
    
    hash1 = hashlib.sha256(csv1.encode("utf-8")).hexdigest()
    hash2 = hashlib.sha256(csv2.encode("utf-8")).hexdigest()
    
    assert hash1 == hash2, "Pipeline output is not identical across repeated runs!"

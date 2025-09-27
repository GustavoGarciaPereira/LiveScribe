from functools import lru_cache

from transformers import pipeline

# app/infrastructure/ml.py
MODEL_NAME = "tabularisai/multilingual-sentiment-analysis"
PIPELINE_TASK = "sentiment-analysis"  # ou "sentiment-analysis"

@lru_cache(maxsize=1)
def get_sentiment_pipeline():
    return pipeline(
        task=PIPELINE_TASK,
        model=MODEL_NAME,
        truncation=True,
    )
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OilPriceImpactOnCunsumerSentimentWIthConfidence(BaseModel):
    market_sentiment: str | None = Field(
        default=None,
        description="The general market sentiment for the day, e.g., Positive, Negative, Neutral.",
    )
    market_sentiment_explanation: str | None = Field(
        default=None,
        description="Explain the main reason for the market sentiment judgment you just expressed.",
    )
    relevant_factors: list[str] | None = Field(
        default=None,
        description="List the most relevant factors (e.g., economic indicators, geopolitical events) that influenced your market sentiment assessment.",
    )
    relevant_news_selection: str | None = Field(
        default=None,
        description="List the specific news headlines that had a significant impact on your market sentiment evaluation.",
    )
    confidence: float | None = Field(
        default=None, description="The confidence for your prediction"
    )

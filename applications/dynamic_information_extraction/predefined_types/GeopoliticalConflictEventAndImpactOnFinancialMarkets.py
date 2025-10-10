from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, Field


class GeopoliticalConflictEventAndImpactOnFinancialMarkets(BaseModel):
    event_name: str | None = None
    event_date: datetime | None = None
    market_impact: str | None = None

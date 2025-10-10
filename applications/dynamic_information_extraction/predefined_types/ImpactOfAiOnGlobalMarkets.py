from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, Field


class ImpactOfAiOnGlobalMarkets(BaseModel):
    AI_Company_Involved: str | None = None
    date: datetime | None = None
    description_of_event: str | None = None
    Impact_on_global_market: str | None = None

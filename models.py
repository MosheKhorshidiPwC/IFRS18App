from __future__ import annotations
from enum import StrEnum
from typing import List
from pydantic import BaseModel, Field, field_validator


class IFRSCategory(StrEnum):
    OPERATING = "operating"
    INVESTING = "investing"
    FINANCING = "financing"
    INCOME_TAX = "income_tax"
    DISCONTINUED = "discontinued_operations"


class LineItem(BaseModel):
    name: str = Field(min_length=1)
    gl_prefixes: List[str] = Field(default_factory=list)
    prefix_length: int = 0
    category: IFRSCategory = IFRSCategory.OPERATING

    @field_validator("gl_prefixes", mode="before")
    @classmethod
    def _normalize_prefixes(cls, value):
        if value is None:
            return []
        return [str(v).strip() for v in value if str(v).strip()]

    @field_validator("prefix_length")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value is None:
            return 0
        if value < 0:
            raise ValueError("prefix_length must be >= 0")
        if value > 32:
            # guard against accidentally huge values
            raise ValueError("prefix_length too large")
        return value


class MappingConfig(BaseModel):
    items: List[LineItem] = Field(default_factory=list)


class UploadedTBColumns(BaseModel):
    account_col: str
    debit_col: str
    credit_col: str

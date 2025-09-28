from __future__ import annotations
from enum import StrEnum
from typing import List
from dataclasses import dataclass, field


class IFRSCategory(StrEnum):
    OPERATING = "operating"
    INVESTING = "investing"
    FINANCING = "financing"
    INCOME_TAX = "income_tax"
    DISCONTINUED = "discontinued_operations"


@dataclass
class LineItem:
    name: str
    gl_prefixes: List[str] = field(default_factory=list)
    prefix_length: int = 0
    category: IFRSCategory = IFRSCategory.OPERATING

    def __post_init__(self) -> None:
        # Normalize name
        self.name = str(self.name).strip() if self.name is not None else ""
        if len(self.name) == 0:
            raise ValueError("name must be a non-empty string")

        # Normalize category from string if needed
        if isinstance(self.category, str):
            self.category = IFRSCategory(self.category)

        # Normalize gl_prefixes: ensure list[str], stripped, no empties
        if self.gl_prefixes is None:
            self.gl_prefixes = []
        normalized_prefixes: List[str] = []
        for value in self.gl_prefixes:
            value_str = str(value).strip()
            if value_str:
                normalized_prefixes.append(value_str)
        self.gl_prefixes = normalized_prefixes

        # Validate/normalize prefix_length
        if self.prefix_length is None:
            self.prefix_length = 0
        try:
            self.prefix_length = int(self.prefix_length)
        except (TypeError, ValueError):
            raise ValueError("prefix_length must be an integer")
        if self.prefix_length < 0:
            raise ValueError("prefix_length must be >= 0")
        if self.prefix_length > 32:
            # guard against accidentally huge values
            raise ValueError("prefix_length too large")


@dataclass
class MappingConfig:
    items: List[LineItem] = field(default_factory=list)


@dataclass
class UploadedTBColumns:
    account_col: str
    debit_col: str
    credit_col: str

    def __post_init__(self) -> None:
        # Basic normalization to keep behavior predictable
        self.account_col = str(self.account_col)
        self.debit_col = str(self.debit_col)
        self.credit_col = str(self.credit_col)

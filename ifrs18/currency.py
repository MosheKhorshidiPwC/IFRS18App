from __future__ import annotations

SUPPORTED_CURRENCIES = [
    "ILS",  # Israeli new shekel
    "USD",
    "EUR",
    "GBP",
]


def format_amount(amount: float, currency: str) -> str:
    try:
        return f"{currency} {amount:,.2f}"
    except Exception:
        return f"{currency} {amount}"

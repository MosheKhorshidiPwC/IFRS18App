from __future__ import annotations

import io
import re
from typing import Dict, Iterable, List

import pandas as pd

MAX_FILE_SIZE_MB = 20
_MAX_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def _ensure_small_enough(file_like) -> None:
    try:
        size = file_like.size  # streamlit InMemoryUploadedFile
    except Exception:
        try:
            size = len(file_like.getvalue())
        except Exception:
            # best effort
            size = 0
    if size and size > _MAX_BYTES:
        raise ValueError(f"File too large. Max {MAX_FILE_SIZE_MB} MB")


def read_trial_balance(file_like, filename: str) -> pd.DataFrame:
    _ensure_small_enough(file_like)
    name_lower = (filename or "").lower()

    # Reset pointer if possible
    try:
        file_like.seek(0)
    except Exception:
        pass

    if name_lower.endswith(".csv"):
        data = file_like.read()
        if isinstance(data, bytes):
            buffer = io.BytesIO(data)
        else:
            buffer = io.BytesIO(bytes(data))
        buffer.seek(0)
        df = pd.read_csv(
            buffer,
            dtype=str,
            encoding_errors="ignore",
        )
    elif name_lower.endswith(".xlsx"):
        df = pd.read_excel(file_like, dtype=str, engine="openpyxl")
    else:
        raise ValueError("Unsupported file type. Use CSV or XLSX.")

    # Normalize column names (strip whitespace; leave original cases)
    df.columns = [str(c).strip() for c in df.columns]
    return df


_CURRENCY_CHARS_PATTERN = re.compile(r"[^0-9\-\.,()]+")
_THOUSAND_SEP_PATTERN = re.compile(r"(?<=\d),(?=\d{3}(\D|$))")


def clean_numeric_series(series: pd.Series) -> pd.Series:
    def _clean_one(x) -> float | None:
        if pd.isna(x):
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip()
        if not s:
            return None
        # Remove currency symbols and stray letters
        s = _CURRENCY_CHARS_PATTERN.sub("", s)
        # Handle parentheses as negatives
        negative = s.startswith("(") and s.endswith(")")
        s = s.replace("(", "").replace(")", "")
        # Remove thousand separators conservatively
        s = _THOUSAND_SEP_PATTERN.sub("", s)
        # If more than one dot, replace all but last
        parts = s.split(".")
        if len(parts) > 2:
            s = "".join(parts[:-1]) + "." + parts[-1]
        # Remove any remaining commas
        s = s.replace(",", "")
        try:
            val = float(s)
        except Exception:
            return None
        return -val if negative else val

    cleaned = series.map(_clean_one)
    return cleaned.astype(float)


def guess_column_mapping(columns: Iterable[str]) -> Dict[str, str]:
    cols = [str(c) for c in columns]
    lowered = {c.lower(): c for c in cols}

    def _find(patterns: List[str]) -> str | None:
        for p in patterns:
            # exact
            if p in lowered:
                return lowered[p]
        # contains
        for c in cols:
            cl = c.lower()
            if any(p in cl for p in patterns):
                return c
        return None

    account = _find(["account number", "account", "gl", "ledger", "acct", "gl account"]) or cols[0]
    debit = _find(["debit", "dr"]) or cols[1 if len(cols) > 1 else 0]
    credit = _find(["credit", "cr"]) or cols[2 if len(cols) > 2 else 0]
    return {"account": account, "debit": debit, "credit": credit}

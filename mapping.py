from __future__ import annotations
from typing import Dict, List, Tuple
import pandas as pd
from models import LineItem, MappingConfig


def _match_line_item_for_account(account: str, items: List[LineItem]) -> Tuple[str | None, str | None]:
    if account is None:
        return None, None
    account_str = str(account)

    best_item: LineItem | None = None
    best_prefix: str | None = None

    for item in items:
        if not item.gl_prefixes:
            continue
        for prefix in item.gl_prefixes:
            p = str(prefix)
            if not p:
                continue
            use_len = item.prefix_length if item.prefix_length and item.prefix_length > 0 else len(p)
            if account_str[:use_len] == p[:use_len]:
                if best_prefix is None or len(p) > len(best_prefix):
                    best_item = item
                    best_prefix = p
    return (best_item.name if best_item else None), best_prefix


def apply_line_item_mapping(
    df: pd.DataFrame,
    account_col: str,
    debit_col: str,
    credit_col: str,
    mapping: MappingConfig,
) -> pd.DataFrame:
    work = df.copy()

    # Ensure numeric
    for col in (debit_col, credit_col):
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)

    # Signed P&L amount: credits positive, debits negative
    work["amount"] = work[credit_col] - work[debit_col]

    # Determine line item per account using best (longest) prefix match
    items = mapping.items or []
    work["line_item"], work["matched_prefix"] = zip(
        *work[account_col].astype(str).map(lambda a: _match_line_item_for_account(a, items))
    )
    work["line_item"] = work["line_item"].fillna("Unmapped")

    totals = (
        work.groupby(["line_item"], dropna=False)["amount"].sum().reset_index()
    )

    # Ensure all configured line items appear even if zero
    configured_names = [li.name for li in items]
    present = set(totals["line_item"].tolist())
    missing = [n for n in configured_names if n not in present]
    if missing:
        zeros = pd.DataFrame({"line_item": missing, "amount": [0.0] * len(missing)})
        totals = pd.concat([totals, zeros], ignore_index=True)

    # Attach categories from mapping
    name_to_cat: Dict[str, str] = {li.name: li.category for li in items}
    totals["category"] = totals["line_item"].map(name_to_cat).fillna("unassigned")

    # Order by category then name for readability
    totals = totals.sort_values(["category", "line_item"]).reset_index(drop=True)
    return totals

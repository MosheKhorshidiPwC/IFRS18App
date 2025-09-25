from __future__ import annotations
import pandas as pd
from models import IFRSCategory


def highlight_row(row):
    if row["label"] == "Gross Profit":  # match your condition
        return ['background-color: lightgrey'] * len(row)
    return ['background-color: white'] * len(row)

def generate_ifrs18_pl(line_totals: pd.DataFrame) -> pd.DataFrame:
    # Expect columns: line_item, amount, category
    df = line_totals.copy()
    if df.empty:
        return pd.DataFrame(
            columns=["label", "amount", "category", "type", "is_subtotal"]
        )

    df["category"] = df["category"].fillna("")

    # Aggregate defensively by line_item
    grouped = df.groupby("line_item", dropna=False)["amount"].sum().reset_index()
    name_to_amount = dict(zip(grouped["line_item"], grouped["amount"]))

    # Map a stable category per line_item (first occurrence wins)
    first_cats = (
        df.drop_duplicates(subset=["line_item"]) [["line_item", "category"]]
        .set_index("line_item")["category"].to_dict()
    )

    # Standardized labels
    revenue_label = "Revenue"
    cost_labels = ["Cost Of Goods","Impairment of Goodwill"]
    gna_label = "General and Administrative Expenses"

    # Pull amounts (default 0.0 if missing)
    revenue_amount = float(name_to_amount.get(revenue_label, 0.0))
    # Prefer the first cost label that exists
    cost_label_present = next((c for c in cost_labels if c in name_to_amount), cost_labels)
    cost_amount = float(name_to_amount.get(cost_label_present, 0.0))
    gna_amount = float(name_to_amount.get(gna_label, 0.0))

    total_expenses = cost_amount + gna_amount
    operating_profit = revenue_amount - total_expenses

    included_labels = {revenue_label, cost_label_present, gna_label}

    presentation_rows = []

    # Revenue section
    if revenue_label in name_to_amount or True:
        presentation_rows.append(
            {
                "label": revenue_label,
                "amount": revenue_amount,
                "category": first_cats.get(revenue_label, IFRSCategory.OPERATING),
                "type": "line",
            }
        )
        presentation_rows.append(
            {
                "label": "Gross Profit",
                "amount": revenue_amount,
                "category": "subtotal",
                "type": "subtotal",

            }
        )

    # Expenses section
    if cost_label_present in name_to_amount:
        presentation_rows.append(
            {
                "label": cost_label_present,
                "amount": cost_amount,
                "category": first_cats.get(cost_label_present, IFRSCategory.OPERATING),
                "type": "line",
            }
        )
    if gna_label in name_to_amount:
        presentation_rows.append(
            {
                "label": gna_label,
                "amount": gna_amount,
                "category": first_cats.get(gna_label, IFRSCategory.OPERATING),
                "type": "line",
            }
        )

    # Remaining lines (if any), keep original order from df
    remaining = [
        {
            "label": row["line_item"],
            "amount": float(row["amount"]),
            "category": row["category"],
            "type": "line",
        }
        for _, row in df.iterrows()
        if row["line_item"] not in included_labels
    ]
    presentation_rows.extend(remaining)

    # Optional: Operating profit subtotal after expenses
    presentation_rows.append(
        {
            "label": "Operating (Loss) profit",
            "amount": operating_profit,
            "category": IFRSCategory.OPERATING,
            "type": "subtotal",
        }
    )

    out = pd.DataFrame(presentation_rows)
    out["is_subtotal"] = out["type"].eq("subtotal")
    return out[["label", "amount", "category", "type"]] #, "is_subtotal"]]

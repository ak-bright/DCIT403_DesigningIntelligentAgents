"""Lab 3 MCP server: pharmacy stock. Run from inside lab03/."""
import csv
from datetime import date, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pharmacy-stock")

DATA = Path(__file__).parent / "data" / "pharmacy_stock.csv"
FIELDS = ["item", "strength", "form", "quantity", "unit_price_ghs", "expiry_date"]


def load() -> list[dict]:
    with open(DATA, newline="") as f:
        return list(csv.DictReader(f))


def save(rows: list[dict]) -> None:
    with open(DATA, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


@mcp.tool()
def check_stock(item: str, strength: str = "") -> list[dict]:
    """Check stock for ONE medicine. Use for questions like 'Do we have amoxicillin 500mg?'.
    item: medicine name, e.g. 'amoxicillin'. strength: optional, e.g. '500mg'.
    Returns matching rows with quantity, unit price in GHS and expiry date; empty list if none."""
    rows = [r for r in load() if item.lower() in r["item"].lower()]
    if strength:
        rows = [r for r in rows if strength.lower() in r["strength"].lower()]
    return rows


@mcp.tool()
def search_items(query: str) -> list[dict]:
    """Search the catalogue by a word in the item name or form (e.g. 'syrup', 'tablet', 'cough').
    Use when the user does not name an exact medicine. Returns matching rows."""
    q = query.lower()
    return [r for r in load() if q in r["item"].lower() or q in r["form"].lower()]


@mcp.tool()
def list_expiring(days: int) -> list[dict]:
    """List items that expire within the next `days` days (including already expired ones).
    Use for questions like 'Which items expire within 60 days?'. days must be a whole number."""
    limit = date.today() + timedelta(days=days)
    return [r for r in load() if date.fromisoformat(r["expiry_date"]) <= limit]


@mcp.tool()
def record_sale(item: str, strength: str, qty: int) -> str:
    """ACTION: record a sale and REDUCE stock. Only call when the user clearly asks to sell/record a sale.
    item: exact medicine name; strength: exact strength, e.g. '500mg'; qty: positive whole number of packs.
    Refuses if qty <= 0, the item is not found, or stock is insufficient."""
    if qty <= 0:
        return "REFUSED: quantity must be a positive whole number."
    rows = load()
    matches = [r for r in rows
               if r["item"].lower() == item.lower() and r["strength"].lower() == strength.lower()]
    if len(matches) != 1:
        return f"REFUSED: expected exactly one match for {item} {strength}, found {len(matches)}."
    row = matches[0]
    have = int(row["quantity"])
    if qty > have:
        return f"REFUSED: only {have} packs of {row['item']} {row['strength']} in stock, cannot sell {qty}."
    row["quantity"] = str(have - qty)
    save(rows)
    total = qty * float(row["unit_price_ghs"])
    return f"OK: sold {qty} x {row['item']} {row['strength']} for GHS {total:.2f}. {have - qty} left."


if __name__ == "__main__":
    mcp.run()
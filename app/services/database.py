"""
database.py — lightweight in-memory store loaded from data/store_data.json.

Provides simple lookup helpers used by the agent tools.
"""

import json
from pathlib import Path
from typing import Any

# ── Load once at import time ──────────────────────────────────────────────────

# def load_data(file_path):
#     with open(file_path, "r") as f:
#         return json.load(f)


# def get_size_chart(brand: str):
#     data = load_data("data/store_data.json")
#     return data.get(brand, data["default"])


with open("data/store_data.json") as f:
    _raw = json.load(f)

# item_id → item dict
CATALOGUE: dict[str, dict[str, Any]] = {item["id"]: item for item in _raw["items"]}


# ── Public helpers ────────────────────────────────────────────────────────────

def list_catalogue() -> list[dict[str, Any]]:
    """Return a lightweight summary of every item in the catalogue."""
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "category": item["category"],
            "brand": item["brand"],
            "price": item["price"],
            "available_sizes": item["sizes"],
        }
        for item in CATALOGUE.values()
    ]


def get_item(item_id: str) -> dict[str, Any] | None:
    """Return full item data (including size_chart) or None if not found."""
    return CATALOGUE.get(item_id)


def get_items_by_ids(item_ids: list[str]) -> list[dict[str, Any]]:
    """Return full data for a list of item IDs (skips unknown IDs)."""
    return [CATALOGUE[iid] for iid in item_ids if iid in CATALOGUE]
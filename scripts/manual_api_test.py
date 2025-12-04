"""
Pequeno teste manual para exercitar o endpoint /api/search.

Execute o FastAPI com:
    uvicorn api.main:app --reload

Em outro terminal rode:
    python scripts/manual_api_test.py
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import requests


def main() -> None:
    payload = {
        "origin": "BEL",
        "destination": "GRU",
    }

    response = requests.get("http://localhost:8000/history", params=payload, timeout=60)
    response.raise_for_status()

    data = response.json()
    print("Status:", response.status_code)
    print("Data:", data)


if __name__ == "__main__":
    main()

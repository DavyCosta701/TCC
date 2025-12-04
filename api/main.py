from __future__ import annotations

import asyncio
import math
import sqlite3
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Make sure repository-level packages resolve when running from api/
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

try:
    from .cities import CIDADES, CITY_ALIASES
except ImportError:  # pragma: no cover
    from api.cities import CIDADES, CITY_ALIASES
from azul_scraper.azul_scraper_api_miles import (
    FlightSearchMiles,
    extract_flight_info as extract_azul_miles_info,
)
from azul_scraper.azul_scraper_api_money import (
    FlightSearchMoney,
    extract_flight_info as extract_azul_money_info,
)
from smiles_scraper.smiles_scraper_interceptor import (
    SmilesFlightSearch,
    extract_flight_info as extract_smiles_info,
)

DEFAULT_PRICE_PER_MILE = 0.02
SQLITE_PATH = REPO_ROOT / "local" / "tcc_history.sqlite"

smiles_search = SmilesFlightSearch()
azul_miles_search = FlightSearchMiles()
azul_cash_search = FlightSearchMoney()

smiles_lock = asyncio.Lock()
azul_miles_lock = asyncio.Lock()
azul_cash_lock = asyncio.Lock()


def _finite_or_none(value: Optional[float]) -> Optional[float]:
    """Return a finite float value or None when missing/invalid."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        float_value = float(value)
        return float_value if math.isfinite(float_value) else None
    return None


def _sum_optional(values: Iterable[Optional[float]]) -> Optional[float]:
    """Sum optional numeric values, returning None when all inputs are missing."""
    total = 0.0
    has_value = False
    for value in values:
        if value is not None:
            total += float(value)
            has_value = True
    return total if has_value else None


def _resolve_city(name: Optional[str]) -> Optional[str]:
    """Map IATA codes or aliases to the persisted city name used in SQLite."""
    if not name:
        return None
    cleaned = name.strip()
    if not cleaned:
        return None
    alias = CITY_ALIASES.get(cleaned)
    if alias:
        return alias
    iata_code = cleaned.upper()
    if iata_code in CIDADES:
        return CIDADES[iata_code]
    return cleaned


def _format_historical_payload(origin_code: str, destination_code: str, row: sqlite3.Row) -> Dict[str, Any]:
    """Normalize a historical row to match the scraper JSON contract."""
    record = dict(row)
    return {
        "route": f"{origin_code} -> {destination_code}",
        "origin_name": record.get("origin"),
        "destination_name": record.get("destination"),
        "departure": record.get("departure_date"),
        "return": record.get("return_date"),
        "outbound": {
            "miles": record.get("outbound_miles"),
            "money": record.get("outbound_cash"),
        },
        "inbound": {
            "miles": record.get("inbound_miles"),
            "money": record.get("inbound_cash"),
        },
        "total": {
            "miles": record.get("total_miles"),
            "money": record.get("total_cash"),
        },
    }


app = FastAPI(title="TCC API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def _search_smiles_flight(origin: str, destination: str, departure_date: date, return_date: date, adults: int = 1):
    """
    Perform a search for a Smiles flight given the input parameters.
    Returns a JSON result standardized to match the structure of the Azul cash/miles search.
    """
    dep_str = departure_date.strftime("%Y-%m-%d")
    ret_str = return_date.strftime("%Y-%m-%d")

    dep_dt = datetime.strptime(dep_str, "%Y-%m-%d")
    ret_dt = datetime.strptime(ret_str, "%Y-%m-%d")
    dep_ts = int(dep_dt.timestamp() * 1000)
    ret_ts = int(ret_dt.timestamp() * 1000)

    async with smiles_lock:
        await smiles_search.initialize_headers(
            origin, destination, dep_ts, ret_ts
        )
        flight_data = await asyncio.to_thread(
            smiles_search.get_flight_info,
            origin,
            destination,
            dep_str,
            ret_str,
        )

    if "error" in flight_data:
        return {
            "route": f"{origin} -> {destination}",
            "departure": dep_str,
            "return": ret_str,
            "error": flight_data["error"],
        }
    flight_info = extract_smiles_info(flight_data)
    if "error" in flight_info:
        return {
            "route": f"{origin} -> {destination}",
            "departure": dep_str,
            "return": ret_str,
            "error": flight_info["error"],
        }
    outbound_miles = _finite_or_none(flight_info.get("lowest_outbound_miles"))
    outbound_money = _finite_or_none(flight_info.get("lowest_outbound_money"))
    inbound_miles = _finite_or_none(flight_info.get("lowest_inbound_miles"))
    inbound_money = _finite_or_none(flight_info.get("lowest_inbound_money"))

    total_miles = _sum_optional([outbound_miles, inbound_miles])
    total_money = _sum_optional([outbound_money, inbound_money])

    # Standardize JSON to match Azul cash/miles search
    json_result = {
        "route": f"{origin} -> {destination}",
        "departure": dep_str,
        "return": ret_str,
        "outbound": {
            "miles": outbound_miles,
            "money": outbound_money,
        },
        "inbound": {
            "miles": inbound_miles,
            "money": inbound_money,
        },
        "total": {
            "miles": total_miles,
            "money": total_money,
        },
    }
    return json_result


async def search_azul_miles_flight(origin: str, destination: str, departure_date: date, return_date: date, adults: int = 1):
    """
    Perform a search for an Azul miles flight given the input parameters.
    Returns a JSON result mirroring the CLI/debug output structure from azul_scraper_api_miles.py.
    """
    dep_str = departure_date.strftime("%m/%d/%Y")
    ret_str = return_date.strftime("%m/%d/%Y")

    async with azul_miles_lock:
        flight_data = await azul_miles_search.get_flight_info(
            origin, destination, dep_str, ret_str
        )

    if "error" in flight_data:
        return {
            "route": f"{origin} -> {destination}",
            "departure": dep_str,
            "return": ret_str,
            "error": flight_data["error"],
        }

    flight_info = extract_azul_miles_info(flight_data)
    if "error" in flight_info:
        return {
            "route": f"{origin} -> {destination}",
            "departure": dep_str,
            "return": ret_str,
            "error": flight_info["error"],
        }

    outbound_miles = _finite_or_none(flight_info.get("lowest_outbound"))
    inbound_miles = _finite_or_none(flight_info.get("lowest_inbound"))
    total_miles = _sum_optional([outbound_miles, inbound_miles])

    json_result = {
        "route": f"{origin} -> {destination}",
        "departure": dep_str,
        "return": ret_str,
        "outbound": {
            "miles": outbound_miles,
        },
        "inbound": {
            "miles": inbound_miles,
        },
        "total": {
            "miles": total_miles,
        },
    }
    return json_result


async def search_azul_cash_flight(origin: str, destination: str, departure_date: date, return_date: date, adults: int = 1):
    """
    Perform a search for an Azul cash flight given the input parameters.
    Returns a JSON result mirroring the CLI/debug output structure from azul_scraper_api_money.py.
    """
    dep_str = departure_date.strftime("%m/%d/%Y")
    ret_str = return_date.strftime("%m/%d/%Y")

    async with azul_cash_lock:
        flight_data = await azul_cash_search.get_flight_info(
            origin, destination, dep_str, ret_str
        )

    if "error" in flight_data:
        return {
            "route": f"{origin} -> {destination}",
            "departure": dep_str,
            "return": ret_str,
            "error": flight_data["error"],
        }

    flight_info = extract_azul_money_info(flight_data)
    if "error" in flight_info:
        return {
            "route": f"{origin} -> {destination}",
            "departure": dep_str,
            "return": ret_str,
            "error": flight_info["error"],
        }

    outbound_money = _finite_or_none(flight_info.get("lowest_outbound"))
    inbound_money = _finite_or_none(flight_info.get("lowest_inbound"))
    total_money = _sum_optional([outbound_money, inbound_money])

    json_result = {
        "route": f"{origin} -> {destination}",
        "departure": dep_str,
        "return": ret_str,
        "outbound": {
            "money": outbound_money,
        },
        "inbound": {
            "money": inbound_money,
        },
        "total": {
            "money": total_money,
        },
    }
    return json_result


@app.get("/search")
async def search_flight(origin: str, destination: str, departure_date: date, return_date: date, adults: int = 1):
    """
    Perform a search for a flight given the input parameters.
    Returns a JSON result standardized to match the structure of the Azul cash/miles search.
    """
    return {
        "smiles": await _search_smiles_flight(origin, destination, departure_date, return_date, adults),
        "azul_miles": await search_azul_miles_flight(origin, destination, departure_date, return_date, adults),
        "azul_cash": await search_azul_cash_flight(origin, destination, departure_date, return_date, adults),
    }


@app.get("/history")
async def search_historical_flight(origin: str, destination: str):
    """
    Retrieve the lowest historical fare registered for the informed route.
    """
    
    # Busca menor valor histórico para o par (origin, destination) no banco SQLite.
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    origin_name = _resolve_city(origin)
    destination_name = _resolve_city(destination)
    if not origin_name or not destination_name:
        return {"error": f"Unknown route identifiers: origin={origin!r}, destination={destination!r}"}
    try:
        cursor = conn.cursor()

        def _fetch_best(column: str) -> Optional[sqlite3.Row]:
            if column not in {"total_miles", "total_cash"}:
                return None
            cursor.execute(
                f"""
                SELECT *
                FROM historical_fares
                WHERE 
                    UPPER(origin) = UPPER(?) AND 
                    UPPER(destination) = UPPER(?) AND
                    {column} IS NOT NULL
                ORDER BY {column} ASC
                LIMIT 1
                """,
                (origin_name, destination_name),
            )
            return cursor.fetchone()

        miles_row = _fetch_best("total_miles")
        cash_row = _fetch_best("total_cash")

        if not miles_row and not cash_row:
            return {"error": f"No historical data found for route {origin_name} -> {destination_name}"}

        response: Dict[str, Any] = {
            "route": f"{origin} -> {destination}",
            "origin_name": origin_name,
            "destination_name": destination_name,
            "best_miles": _format_historical_payload(origin, destination, miles_row) if miles_row else None,
            "best_money": _format_historical_payload(origin, destination, cash_row) if cash_row else None,
        }
        return response
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
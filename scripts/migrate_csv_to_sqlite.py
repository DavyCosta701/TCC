"""
Importa os dados históricos contidos em `local/BD_alerta de voos com milhas.csv`
para um banco SQLite, preservando somente as colunas relevantes para o TCC.

Uso:
    python scripts/migrate_csv_to_sqlite.py \\
        --csv local/BD_alerta\\ de\\ voos\\ com\\ milhas.csv \\
        --database local/tcc_history.sqlite
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence


@dataclass
class HistoricalRow:
    origin: str
    destination: str
    departure_date: Optional[str]
    return_date: Optional[str]
    outbound_miles: Optional[int]
    inbound_miles: Optional[int]
    total_miles: Optional[int]
    outbound_cash: Optional[float]
    inbound_cash: Optional[float]
    total_cash: Optional[float]

    def as_tuple(self) -> tuple:
        return (
            self.origin,
            self.destination,
            self.departure_date,
            self.return_date,
            self.outbound_miles,
            self.inbound_miles,
            self.total_miles,
            self.outbound_cash,
            self.inbound_cash,
            self.total_cash,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migra dados do CSV histórico para um SQLite simplificado."
    )
    parser.add_argument(
        "--csv",
        default="local/BD_alerta de voos com milhas.csv",
        help="Caminho para o CSV de origem.",
    )
    parser.add_argument(
        "--database",
        default="local/tcc_history.sqlite",
        help="Caminho do banco SQLite de destino.",
    )
    return parser.parse_args()


def _only_digits(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits or None


def normalize_miles(value: Optional[str]) -> Optional[int]:
    digits = _only_digits(value)
    if not digits:
        return None
    return int(digits)


def normalize_money(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    digits = _only_digits(value)
    if not digits:
        return None
    amount = int(digits)
    if any(sep in value for sep in (",", ".")):
        return amount / 100.0
    return float(amount)


def normalize_month(value: Optional[str], pick_last: bool = False) -> Optional[int]:
    if not value:
        return None
    parts = [segment for segment in value.split("-") if segment]
    if not parts:
        return None
    target = parts[-1] if pick_last and len(parts) > 1 else parts[0]
    if not target.isdigit():
        return None
    month = int(target)
    if 1 <= month <= 12:
        return month
    return None


def build_date(year: Optional[str], month: Optional[str], pick_last: bool = False) -> Optional[str]:
    """Create YYYY-MM-01 strings from year/month metadata, defaulting to the first day."""
    if not year:
        return None
    try:
        year_int = int(year)
    except ValueError:
        return None
    month_int = normalize_month(month, pick_last=pick_last)
    if month_int is None:
        return None
    return date(year_int, month_int, 1).isoformat()


def iter_csv_rows(csv_path: Path) -> Iterator[dict]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(skip_preamble(handle))
        for row in reader:
            yield row


def skip_preamble(handle: Iterable[str]) -> Iterator[str]:
    for line in handle:
        if line.lower().startswith("ano,"):
            yield line
            break
    else:
        raise RuntimeError("Cabeçalho 'Ano,Mês,...' não encontrado no CSV.")

    for line in handle:
        yield line


def build_row(raw: dict) -> Optional[HistoricalRow]:
    origin = (raw.get("Local-Origem") or "").strip()
    destination = (raw.get("Local-Destino") or "").strip()
    if not (origin and destination):
        return None

    return HistoricalRow(
        origin=origin,
        destination=destination,
        departure_date=build_date(raw.get("Ano-Ida"), raw.get("Mês-Ida")),
        return_date=build_date(raw.get("Ano-Volta"), raw.get("Mês-Volta"), pick_last=True),
        outbound_miles=normalize_miles(raw.get("Milhas-Ida")),
        inbound_miles=normalize_miles(raw.get("Milhas-Volta")),
        total_miles=normalize_miles(raw.get("Total-Milhas")),
        outbound_cash=normalize_money(raw.get("Ida-Real")),
        inbound_cash=normalize_money(raw.get("Volta-Real")),
        total_cash=normalize_money(raw.get("Total-Real")),
    )


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS historical_fares")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS historical_fares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT,
            return_date TEXT,
            outbound_miles INTEGER,
            inbound_miles INTEGER,
            total_miles INTEGER,
            outbound_cash REAL,
            inbound_cash REAL,
            total_cash REAL
        )
        """
    )


def insert_rows(conn: sqlite3.Connection, rows: Sequence[HistoricalRow]) -> None:
    conn.executemany(
        """
        INSERT INTO historical_fares (
            origin,
            destination,
            departure_date,
            return_date,
            outbound_miles,
            inbound_miles,
            total_miles,
            outbound_cash,
            inbound_cash,
            total_cash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [row.as_tuple() for row in rows],
    )


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    db_path = Path(args.database)

    if not csv_path.exists():
        sys.exit(f"CSV não encontrado: {csv_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    parsed_rows: List[HistoricalRow] = []
    for raw in iter_csv_rows(csv_path):
        row = build_row(raw)
        if row:
            parsed_rows.append(row)

    if not parsed_rows:
        sys.exit("Nenhuma linha válida encontrada para inserção.")

    with sqlite3.connect(db_path) as conn:
        ensure_schema(conn)
        insert_rows(conn, parsed_rows)
        conn.commit()

    print(f"Inseridas {len(parsed_rows)} linhas em {db_path}")


if __name__ == "__main__":
    main()

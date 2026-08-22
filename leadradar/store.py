from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable, List, Optional, Union

from .models import Company

STANDAARD_DB_PAD = Path(__file__).parent.parent / "data" / "leads.db"

# Volgorde bepaalt ook de volgorde in de status-dropdown in de UI.
STATUSSEN = ["nieuw", "interessant", "contact gelegd", "klant", "niet interessant"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profiel_naam TEXT NOT NULL,
    bedrijfsnaam TEXT NOT NULL,
    plaats TEXT,
    postcode TEXT,
    sector TEXT,
    score REAL,
    match_redenen TEXT,
    contactpersoon TEXT,
    contactpersoon_bron TEXT,
    kvk_status TEXT,
    website_status TEXT,
    concept_bericht TEXT,
    bron TEXT,
    status TEXT NOT NULL DEFAULT 'nieuw',
    toegevoegd_op TEXT NOT NULL DEFAULT (datetime('now')),
    bijgewerkt_op TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(profiel_naam, bedrijfsnaam, plaats)
);
"""


class LeadStore:
    """Persistente, doorzoekbare leadlijst (SQLite). Eén rij = één bedrijf binnen één profiel.

    Een nieuwe zoekopdracht overschrijft nooit stilzwijgend een eerder gezette status: bij een
    hernieuwde run op hetzelfde profiel + bedrijf + plaats worden alleen de verrijkings- en
    scoregegevens bijgewerkt, de status ('interessant', 'niet interessant', ...) blijft staan.

    Let op (Streamlit Community Cloud): dit bestand leeft op de lokale schijf van de
    deployment-container. Het overleeft app-herstarts binnen dezelfde deployment, maar niet
    gegarandeerd een nieuwe deploy — voor een klant die dit moet vertrouwen als permanente
    opslag is een externe database (bijv. gehoste Postgres/SQLite) een logische volgende stap.
    """

    def __init__(self, db_pad: Union[str, Path] = STANDAARD_DB_PAD) -> None:
        self.db_pad = Path(db_pad)
        self.db_pad.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as con:
            con.execute(_SCHEMA)
            con.commit()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_pad)
        con.row_factory = sqlite3.Row
        return con

    def upsert_bedrijven(self, bedrijven: Iterable[Company], profiel_naam: str) -> int:
        bedrijven = list(bedrijven)
        with closing(self._connect()) as con:
            con.executemany(
                """
                INSERT INTO leads (
                    profiel_naam, bedrijfsnaam, plaats, postcode, sector, score,
                    match_redenen, contactpersoon, contactpersoon_bron, kvk_status,
                    website_status, concept_bericht, bron
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profiel_naam, bedrijfsnaam, plaats) DO UPDATE SET
                    postcode=excluded.postcode,
                    sector=excluded.sector,
                    score=excluded.score,
                    match_redenen=excluded.match_redenen,
                    contactpersoon=excluded.contactpersoon,
                    contactpersoon_bron=excluded.contactpersoon_bron,
                    kvk_status=excluded.kvk_status,
                    website_status=excluded.website_status,
                    concept_bericht=excluded.concept_bericht,
                    bron=excluded.bron,
                    bijgewerkt_op=datetime('now')
                """,
                [
                    (
                        profiel_naam,
                        b.bedrijfsnaam,
                        b.plaats,
                        b.postcode,
                        b.sector_bron,
                        b.score,
                        "; ".join(b.match_redenen),
                        b.contactpersoon,
                        b.contactpersoon_bron,
                        b.kvk_status,
                        b.website_status,
                        b.concept_bericht,
                        b.bron,
                    )
                    for b in bedrijven
                ],
            )
            con.commit()
        return len(bedrijven)

    def haal_leads(
        self, profiel_naam: Optional[str] = None, statussen: Optional[List[str]] = None
    ) -> List[sqlite3.Row]:
        query = "SELECT * FROM leads"
        voorwaarden: List[str] = []
        params: List[object] = []
        if profiel_naam:
            voorwaarden.append("profiel_naam = ?")
            params.append(profiel_naam)
        if statussen:
            voorwaarden.append(f"status IN ({','.join('?' * len(statussen))})")
            params.extend(statussen)
        if voorwaarden:
            query += " WHERE " + " AND ".join(voorwaarden)
        query += " ORDER BY score DESC"
        with closing(self._connect()) as con:
            return con.execute(query, params).fetchall()

    def profielnamen(self) -> List[str]:
        with closing(self._connect()) as con:
            rijen = con.execute(
                "SELECT DISTINCT profiel_naam FROM leads ORDER BY profiel_naam"
            ).fetchall()
        return [r["profiel_naam"] for r in rijen]

    def zet_status(self, lead_id: int, status: str) -> None:
        self.zet_statussen_bulk([lead_id], status)

    def zet_statussen_bulk(self, ids: List[int], status: str) -> None:
        if not ids:
            return
        with closing(self._connect()) as con:
            con.executemany(
                "UPDATE leads SET status = ?, bijgewerkt_op = datetime('now') WHERE id = ?",
                [(status, i) for i in ids],
            )
            con.commit()

    def verwijder(self, ids: List[int]) -> None:
        if not ids:
            return
        with closing(self._connect()) as con:
            con.executemany("DELETE FROM leads WHERE id = ?", [(i,) for i in ids])
            con.commit()


def row_naar_company(row: sqlite3.Row) -> Company:
    """Zet een opgeslagen lead-rij weer om naar een Company, zodat schrijf_excel() hergebruikt
    kan worden voor exports vanuit 'Mijn leads'."""
    bedrijf = Company(bedrijfsnaam=row["bedrijfsnaam"], plaats=row["plaats"] or "")
    bedrijf.postcode = row["postcode"]
    bedrijf.sector_bron = row["sector"]
    bedrijf.score = row["score"]
    bedrijf.match_redenen = [r for r in (row["match_redenen"] or "").split("; ") if r]
    bedrijf.contactpersoon = row["contactpersoon"]
    bedrijf.contactpersoon_bron = row["contactpersoon_bron"]
    bedrijf.kvk_status = row["kvk_status"] or "niet opgezocht"
    bedrijf.website_status = row["website_status"] or "niet opgezocht"
    bedrijf.concept_bericht = row["concept_bericht"]
    bedrijf.bron = row["bron"] or "onbekend"
    return bedrijf

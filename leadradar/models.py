from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Company:
    """Eén bedrijf, van ruwe bron-rij tot verrijkt en gescoord lead."""

    # --- uit de bron (bijv. export van bedrijvenopdekaart.nl) ---
    bedrijfsnaam: str
    plaats: str
    postcode: Optional[str] = None
    sector_bron: Optional[str] = None
    grootte_indicatie: Optional[int] = None
    signalen_bron: Dict[str, bool] = field(default_factory=dict)
    website: Optional[str] = None
    bron: str = "onbekend"

    # --- verrijking via KvK ---
    kvk_nummer: Optional[str] = None
    kvk_naam_officieel: Optional[str] = None
    sbi_codes_kvk: List[str] = field(default_factory=list)
    sbi_omschrijvingen_kvk: List[str] = field(default_factory=list)
    medewerkers_kvk: Optional[int] = None
    kvk_status: str = "niet opgezocht"  # "gevonden" | "geen match" | "fout: ..." | "niet opgezocht"

    # --- scoring ---
    score: Optional[float] = None
    match_redenen: List[str] = field(default_factory=list)

    # --- contact & website-verrijking (fase 2, zie leadradar/enrich/website.py) ---
    contactpersoon: Optional[str] = None
    contactpersoon_bron: Optional[str] = None  # bijv. "website (ongeverifieerd)"
    website_status: str = "niet opgezocht"  # "verwerkt" | "geen website bekend" | "website niet bereikbaar" | "niet opgezocht"

    # --- outreach (fase 2, zie leadradar/outreach.py) ---
    concept_bericht: Optional[str] = None

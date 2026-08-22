from __future__ import annotations

from pathlib import Path
from typing import List, Union

import openpyxl
from openpyxl.styles import Font

from .models import Company

KOLOMMEN = [
    ("bedrijfsnaam", "Bedrijf"),
    ("kvk_naam_officieel", "Officiële naam (KvK)"),
    ("kvk_nummer", "KvK-nummer"),
    ("plaats", "Plaats"),
    ("sector_weergave", "Sector"),
    ("grootte_weergave", "Grootte"),
    ("contactpersoon", "Contactpersoon"),
    ("contactpersoon_bron_weergave", "Contactpersoon — bron"),
    ("match_redenen_weergave", "Match-reden"),
    ("score", "Score"),
    ("bron", "Bron"),
    ("kvk_status", "KvK-status"),
    ("website_status", "Website-verrijking"),
    ("concept_bericht_weergave", "Concept bericht"),
]


def _sector_weergave(b: Company) -> str:
    if b.sbi_omschrijvingen_kvk:
        return "; ".join(b.sbi_omschrijvingen_kvk[:2])
    return b.sector_bron or ""


def _grootte_weergave(b: Company) -> str:
    if b.medewerkers_kvk is not None:
        return f"{b.medewerkers_kvk} (KvK)"
    if b.grootte_indicatie is not None:
        return f"~{b.grootte_indicatie} (bron, onbevestigd)"
    return "onbekend"


def schrijf_excel(bedrijven: List[Company], pad: Union[str, Path]) -> None:
    for b in bedrijven:
        b.sector_weergave = _sector_weergave(b)  # type: ignore[attr-defined]
        b.grootte_weergave = _grootte_weergave(b)  # type: ignore[attr-defined]
        b.match_redenen_weergave = "; ".join(b.match_redenen)  # type: ignore[attr-defined]
        b.contactpersoon_bron_weergave = b.contactpersoon_bron or ""  # type: ignore[attr-defined]
        b.concept_bericht_weergave = b.concept_bericht or ""  # type: ignore[attr-defined]
        b.contactpersoon = b.contactpersoon or "— (niet gevonden, zie 'Website-verrijking')"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Leads"

    ws.append([label for _, label in KOLOMMEN])
    for cel in ws[1]:
        cel.font = Font(bold=True)

    for b in sorted(bedrijven, key=lambda x: x.score or 0, reverse=True):
        ws.append([getattr(b, veld, "") for veld, _ in KOLOMMEN])

    for kolom in ws.columns:
        breedte = max((len(str(c.value)) for c in kolom if c.value is not None), default=10)
        ws.column_dimensions[kolom[0].column_letter].width = min(max(breedte + 2, 12), 48)

    ws.freeze_panes = "A2"
    wb.save(pad)

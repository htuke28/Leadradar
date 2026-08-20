from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Union

from ..models import Company

WAAR_WAARDEN = {"1", "true", "waar", "ja", "yes", "y", "x"}


def _naar_bool(waarde: object) -> bool:
    if waarde is None:
        return False
    return str(waarde).strip().lower() in WAAR_WAARDEN


def laad_csv(pad: Union[str, Path], bron_label: str = "csv-import") -> List[Company]:
    """Laad een export (bijv. van bedrijvenopdekaart.nl) in het verwachte kolomformaat.

    Verwachte kolommen (zie data/voorbeeld_export.csv):
    bedrijfsnaam, plaats, postcode, sector, grootte_indicatie,
    vacature_elektromonteur, geen_eigen_elektrotechnicus, website, bron
    """
    bedrijven: List[Company] = []
    with open(pad, newline="", encoding="utf-8") as f:
        lezer = csv.DictReader(f)
        for rij in lezer:
            naam = (rij.get("bedrijfsnaam") or "").strip()
            if not naam:
                continue
            grootte_raw = (rij.get("grootte_indicatie") or "").strip()
            bedrijven.append(
                Company(
                    bedrijfsnaam=naam,
                    plaats=(rij.get("plaats") or "").strip(),
                    postcode=(rij.get("postcode") or "").strip() or None,
                    sector_bron=(rij.get("sector") or "").strip() or None,
                    grootte_indicatie=int(grootte_raw) if grootte_raw.isdigit() else None,
                    signalen_bron={
                        "vacature_elektromonteur": _naar_bool(rij.get("vacature_elektromonteur")),
                        "geen_eigen_elektrotechnicus": _naar_bool(rij.get("geen_eigen_elektrotechnicus")),
                    },
                    website=(rij.get("website") or "").strip() or None,
                    bron=(rij.get("bron") or "").strip() or bron_label,
                )
            )
    return bedrijven

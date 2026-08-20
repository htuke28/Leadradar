from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Union

import yaml

STANDAARD_GEWICHTEN = {"sector": 30, "grootte": 20, "regio": 20, "signaal": 30}


@dataclass
class Profile:
    """Het ideale-klantprofiel (ICP). Eén YAML-bestand per klant/klanttype."""

    naam: str
    sectoren: List[str]
    sbi_codes: List[str]
    grootte_min: int
    grootte_max: int
    regio_omschrijving: str
    type: str
    signalen: List[str]
    gewichten: Dict[str, float] = field(default_factory=lambda: dict(STANDAARD_GEWICHTEN))

    @classmethod
    def from_yaml(cls, pad: Union[str, Path]) -> "Profile":
        with open(pad, "r", encoding="utf-8") as f:
            ruw = yaml.safe_load(f)
        p = ruw["profiel"]
        return cls(
            naam=p["naam"],
            sectoren=list(p.get("sectoren", [])),
            sbi_codes=[str(c) for c in p.get("sbi_codes", [])],
            grootte_min=int(p.get("grootte_min", 0)),
            grootte_max=int(p.get("grootte_max", 10_000)),
            regio_omschrijving=(p.get("regio", {}) or {}).get("omschrijving", ""),
            type=p.get("type", "eindklant"),
            signalen=list(p.get("signalen", [])),
            gewichten={**STANDAARD_GEWICHTEN, **(p.get("gewichten") or {})},
        )

from __future__ import annotations

from typing import List

from ..models import Company
from ..profile import Profile

_FALLBACK_PLAATSEN = ["Enschede", "Hengelo", "Zwolle", "Deventer", "Apeldoorn"]
_FALLBACK_SECTOREN = ["Machinebouw", "Metaalbewerking"]

# Fictieve bedrijfsnamen, bewust generiek (geen bestaande bedrijven) — een mix van duidelijke
# matches, twijfelgevallen en mismatches op grootte, zodat scoring/filtering ook in demomodus
# iets laat zien i.p.v. één identieke rij te herhalen.
_SJABLONEN = [
    {"naam": "Norvex", "grootte_offset": 5, "vacature": True, "geen_eigen": True},
    {"naam": "Kaltec Precisietechniek", "grootte_offset": 15, "vacature": True, "geen_eigen": False},
    {"naam": "Bramco Apparatenbouw", "grootte_offset": 0, "vacature": False, "geen_eigen": True},
    {"naam": "Solvex Metaalwerken", "grootte_offset": -8, "vacature": False, "geen_eigen": False},
    {"naam": "Dravonic Systeembouw", "grootte_offset": 40, "vacature": True, "geen_eigen": True},
    {"naam": "Kendrix Constructie", "grootte_offset": 10, "vacature": False, "geen_eigen": False},
    {"naam": "Overmaat Zwaartechniek", "grootte_offset": 250, "vacature": True, "geen_eigen": False},
    {"naam": "Sallandix Machinebouw", "grootte_offset": 8, "vacature": True, "geen_eigen": True},
]


class DemoClient:
    """Genereert realistisch ogende, volledig fictieve bedrijven op basis van het gekozen
    profiel, zodat de automatische zoek + filter + score-flow (zoals OpenKvK/Google Places
    die zouden leveren) te bekijken en te proberen is zonder een betaalde API-key.

    Nooit een echte bron: elk resultaat krijgt `bron` gevuld met een label dat 'demo' bevat,
    en de UI toont daarbovenop een waarschuwing dat dit geen echte bedrijven zijn.
    """

    def __init__(self, bron_label: str = "demo (fictief, geen echte API-key)") -> None:
        self.bron_label = bron_label

    def zoek(self, profiel: Profile) -> List[Company]:
        plaatsen = profiel.regio_plaatsen or _FALLBACK_PLAATSEN
        sectoren = profiel.sectoren or _FALLBACK_SECTOREN

        bedrijven: List[Company] = []
        for i, sjabloon in enumerate(_SJABLONEN):
            plaats = plaatsen[i % len(plaatsen)]
            sector = sectoren[i % len(sectoren)]
            grootte = max(1, profiel.grootte_min + sjabloon["grootte_offset"])
            naam = f"{sjabloon['naam']} {plaats} B.V."
            slug = naam.lower().replace(" ", "-").replace(".", "").replace("(", "").replace(")", "")

            bedrijven.append(
                Company(
                    bedrijfsnaam=naam,
                    plaats=plaats,
                    sector_bron=sector,
                    grootte_indicatie=grootte,
                    signalen_bron={
                        "vacature_elektromonteur": sjabloon["vacature"],
                        "geen_eigen_elektrotechnicus": sjabloon["geen_eigen"],
                    },
                    website=f"https://www.{slug}.nl",
                    bron=self.bron_label,
                    email=f"info@{slug}.nl",
                    telefoonnummer=f"053-{(200000 + i * 11111) % 1000000:06d}",
                )
            )
        return bedrijven

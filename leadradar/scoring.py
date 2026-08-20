from __future__ import annotations

from typing import List, Optional

from .models import Company
from .profile import Profile


def _sector_matcht(bedrijf: Company, profiel: Profile) -> bool:
    if profiel.sbi_codes and bedrijf.sbi_codes_kvk:
        return any(code in profiel.sbi_codes for code in bedrijf.sbi_codes_kvk)
    if bedrijf.sector_bron:
        return any(s.lower() in bedrijf.sector_bron.lower() for s in profiel.sectoren)
    return False


def _grootte_matcht(bedrijf: Company, profiel: Profile) -> Optional[bool]:
    aantal = bedrijf.medewerkers_kvk if bedrijf.medewerkers_kvk is not None else bedrijf.grootte_indicatie
    if aantal is None:
        return None  # onbevestigd — geen bron had een aantal
    return profiel.grootte_min <= aantal <= profiel.grootte_max


def _signalen_matches(bedrijf: Company, profiel: Profile) -> List[str]:
    return [s for s in profiel.signalen if bedrijf.signalen_bron.get(s)]


def score_bedrijf(bedrijf: Company, profiel: Profile) -> Company:
    """Regelgebaseerde score 0-100 met een leesbare match-reden per bedrijf.

    Regio telt altijd mee: we gaan ervan uit dat de bron (bijv. bedrijvenopdekaart.nl-export)
    al op regio gefilterd is bij het downloaden — dat is geen aanname die deze tool zelf verifieert.
    """
    redenen: List[str] = []
    totaal = 0.0
    gewichten = profiel.gewichten

    if _sector_matcht(bedrijf, profiel):
        totaal += gewichten.get("sector", 0)
        redenen.append("sector komt overeen")

    grootte_ok = _grootte_matcht(bedrijf, profiel)
    if grootte_ok is True:
        totaal += gewichten.get("grootte", 0)
        redenen.append(f"grootte binnen {profiel.grootte_min}-{profiel.grootte_max}")
    elif grootte_ok is None:
        redenen.append("grootte onbevestigd")

    totaal += gewichten.get("regio", 0)
    redenen.append(
        f"regio voorgefilterd bij bron ({profiel.regio_omschrijving})"
        if profiel.regio_omschrijving
        else "regio voorgefilterd bij bron"
    )

    gevonden_signalen = _signalen_matches(bedrijf, profiel)
    if profiel.signalen:
        aandeel = len(gevonden_signalen) / len(profiel.signalen)
        totaal += gewichten.get("signaal", 0) * aandeel
        if gevonden_signalen:
            redenen.append("signaal: " + ", ".join(gevonden_signalen))

    bedrijf.score = round(totaal, 1)
    bedrijf.match_redenen = redenen
    return bedrijf

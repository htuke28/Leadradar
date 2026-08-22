from __future__ import annotations

from .models import Company
from .profile import Profile

# Concept eerste bericht (bouwbrief punt 4, stap 6: "Optioneel: concept eerste bericht in
# Gilberts stijl, klaar om te checken en versturen."). Dit is bewust GEEN "verstuur
# automatisch"-functie — de bouwbrief is expliciet over "mens in de lus": de tool doet het
# voorwerk, Gilbert checkt en beslist. Dit sjabloon is een neutraal vertrekpunt, niet
# "Gilberts stijl" — die kennen we niet. Vervang STANDAARD_SJABLOON zodra er echte
# voorbeeldberichten van Gilbert beschikbaar zijn, dat is het enige dat dit sjabloon
# daadwerkelijk representatief maakt.

STANDAARD_SJABLOON = (
    "Hoi {aanhef},\n\n"
    "Ik kwam {bedrijfsnaam} tegen en zag dat jullie actief zijn in {sector}. "
    "{signaal_zin}"
    "Ik werk vanuit Salesia Techniek en help bedrijven zoals die van jullie met "
    "[korte, concrete waarde — pas dit aan voor je verstuurt].\n\n"
    "Zou een kort gesprek nuttig zijn om te kijken of dit voor jullie relevant is?\n\n"
    "Groet,\nGilbert"
)


def genereer_bericht(bedrijf: Company, profiel: Profile, sjabloon: str = STANDAARD_SJABLOON) -> str:
    """Vult het sjabloon met wat er over dit bedrijf bekend is. Ontbrekende velden (geen
    contactpersoon, geen gevonden signaal) leiden tot een nette, generieke formulering in
    plaats van een kapotte placeholder — het bericht blijft altijd bruikbaar als concept."""
    aanhef = bedrijf.contactpersoon or "daar"
    sector = bedrijf.sector_bron or (profiel.sectoren[0] if profiel.sectoren else "jullie sector")

    gevonden_signalen = [s for s in profiel.signalen if bedrijf.signalen_bron.get(s)]
    if gevonden_signalen:
        signaal_zin = f"Ik zag daarnaast een signaal dat mogelijk relevant is: {', '.join(gevonden_signalen)}. "
    else:
        signaal_zin = ""

    return sjabloon.format(
        aanhef=aanhef,
        bedrijfsnaam=bedrijf.bedrijfsnaam,
        sector=sector,
        signaal_zin=signaal_zin,
    )

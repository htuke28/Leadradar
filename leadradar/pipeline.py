from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from .enrich.kvk import KvkClient
from .enrich.website import WebsiteEnricher
from .models import Company
from .outreach import STANDAARD_SJABLOON, genereer_bericht
from .output import schrijf_excel
from .profile import Profile
from .scoring import score_bedrijf
from .sources.csv_source import laad_csv
from .sources.google_places_source import GooglePlacesClient
from .sources.openkvk_source import OpenKvkClient


def run(
    profiel_pad: Union[str, Path],
    output_pad: Union[str, Path],
    input_csv: Optional[Union[str, Path]] = None,
    openkvk_apikey: Optional[str] = None,
    openkvk_client: Optional[OpenKvkClient] = None,
    google_places_apikey: Optional[str] = None,
    google_places_client: Optional[GooglePlacesClient] = None,
    kvk_client: Optional[KvkClient] = None,
    verrijken_kvk: bool = False,
    verrijken_website: bool = False,
    website_client: Optional[WebsiteEnricher] = None,
    genereer_outreach: bool = False,
    outreach_sjabloon: str = STANDAARD_SJABLOON,
) -> List[Company]:
    """Eén run = één profiel verwerken tot een gescoorde Excel-lijst.

    Bron is precies één van: automatische discovery via OpenKvK (sector x plaats, exacte
    SBI-match), automatische discovery via Google Places (vrije tekst x plaats, sterker
    voor lokaal vindbare bedrijven), of een handmatig aangeleverde CSV.

    Verrijking gebeurt vóór het scoren, zodat een net gevonden signaal (bijv. een
    vacature-elektromonteur op de eigen website) nog meetelt in de score. Outreach-berichten
    worden pas ná het scoren gegenereerd, zodat het bericht de uiteindelijke match-redenen
    kan gebruiken.
    """
    profiel = Profile.from_yaml(profiel_pad)

    bronnen_gegeven = sum(bool(x) for x in (openkvk_client or openkvk_apikey, google_places_client or google_places_apikey, input_csv))
    if bronnen_gegeven != 1:
        raise ValueError(
            "Geef precies één bron op: 'openkvk_apikey', 'google_places_apikey' of 'input_csv'."
        )

    if openkvk_client is not None or openkvk_apikey:
        client = openkvk_client or OpenKvkClient(apikey=openkvk_apikey)
        bedrijven = client.zoek(profiel)
    elif google_places_client is not None or google_places_apikey:
        client = google_places_client or GooglePlacesClient(apikey=google_places_apikey)
        bedrijven = client.zoek(profiel)
    else:
        bedrijven = laad_csv(input_csv)

    if verrijken_kvk:
        kvk = kvk_client or KvkClient()
        bedrijven = [kvk.verrijk(b) for b in bedrijven]

    if verrijken_website:
        website = website_client or WebsiteEnricher()
        bedrijven = [website.verrijk(b, gewenste_signalen=profiel.signalen) for b in bedrijven]

    bedrijven = [score_bedrijf(b, profiel) for b in bedrijven]

    if genereer_outreach:
        for b in bedrijven:
            b.concept_bericht = genereer_bericht(b, profiel, sjabloon=outreach_sjabloon)

    schrijf_excel(bedrijven, output_pad)
    return bedrijven

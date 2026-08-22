from __future__ import annotations

from typing import Dict, List, Optional

import requests

from ..models import Company
from ..profile import Profile

# Google Places API (Text Search, "New") — een derde, optionele discovery-bron naast
# OpenKvK en CSV. Waar OpenKvK precies op officiële SBI-code zoekt (sterk voor
# industriële/B2B-sectoren zoals machinebouw), zoekt Places op vrije tekst + locatie zoals
# een consument zou zoeken ("elektricien in Hengelo") — sterker voor bedrijven die
# vindbaar zijn via een Google Bedrijfsprofiel (winkels, installateurs, lokale
# dienstverleners), zwakker voor niche B2B-industrie zonder zo'n profiel.
#
# Belangrijk om te weten voordat je hierop bouwt:
# - Er is doorgaans een maandelijks tegoed op je Google Cloud-factuur (vaak genoemd: $200),
#   maar het exacte bedrag en de voorwaarden veranderen — controleer dit in de Cloud
#   Console (console.cloud.google.com/google/maps-apis) voordat je hierop rekent.
# - Je moet facturering aanzetten op je Google Cloud-project om een key te krijgen, ook al
#   val je binnen het gratis tegoed — zonder geldige creditcard geen key.
# - "Text Search (New)" levert maximaal 60 resultaten per zoekopdracht (over alle pagina's
#   heen) — dat is een Google-limiet, geen keuze van deze tool.
# - Er komt geen medewerkersaantal uit deze bron (net als bij OpenKvK) — blijft
#   "onbevestigd", telt niet mee bij de grootte-score.

BASE_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.websiteUri,places.nationalPhoneNumber,places.types"
)
MAX_RESULTATEN_PER_COMBINATIE = 60  # Google's eigen limiet per zoekopdracht


class GooglePlacesClient:
    def __init__(self, apikey: str, base_url: str = BASE_URL, timeout: float = 10.0) -> None:
        self.apikey = apikey
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.apikey,
                "X-Goog-FieldMask": FIELD_MASK,
            }
        )

    def _zoek_pagina(self, query: str, page_token: Optional[str] = None) -> dict:
        body: Dict[str, object] = {"textQuery": query}
        if page_token:
            body["pageToken"] = page_token
        resp = self.session.post(self.base_url, json=body, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _naar_company(self, item: dict, sector_term: str, plaats: str) -> Optional[Company]:
        naam = (item.get("displayName") or {}).get("text")
        if not naam:
            return None
        types = item.get("types") or []
        bedrijf = Company(
            bedrijfsnaam=naam,
            plaats=plaats,
            postcode=None,
            sector_bron="; ".join(types) or sector_term,
            grootte_indicatie=None,
            signalen_bron={},
            website=item.get("websiteUri"),
            bron="Google Places",
        )
        bedrijf.kvk_status = "gevonden via Google Places (geen KvK-koppeling)"
        return bedrijf

    def zoek(self, profiel: Profile) -> List[Company]:
        gevonden: Dict[str, Company] = {}

        sector_termen = profiel.sectoren or [None]
        plaatsen = profiel.regio_plaatsen or [None]

        for sector_term in sector_termen:
            for plaats in plaatsen:
                if not sector_term or not plaats:
                    continue
                query = f"{sector_term} in {plaats}, Nederland"
                page_token = None
                opgehaald = 0
                while opgehaald < MAX_RESULTATEN_PER_COMBINATIE:
                    data = self._zoek_pagina(query, page_token)
                    items = data.get("places") or []
                    if not items:
                        break
                    for item in items:
                        bedrijf = self._naar_company(item, sector_term, plaats)
                        if bedrijf is None:
                            continue
                        sleutel = item.get("id") or f"{bedrijf.bedrijfsnaam}|{bedrijf.plaats}"
                        gevonden.setdefault(sleutel, bedrijf)
                    opgehaald += len(items)
                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break

        return list(gevonden.values())

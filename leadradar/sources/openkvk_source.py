from __future__ import annotations

from typing import Dict, List, Optional

import requests

from ..models import Company
from ..profile import Profile

# OpenKvK via overheid.io — een doorzoekbare, gratis-te-registreren index van het
# Handelsregister MET bedrijfsnamen (in tegenstelling tot KvK's eigen open dataset, die
# uit privacyoverweging geen namen bevat). Dit is de bron die daadwerkelijk "automatisch
# bedrijven verzamelen op profiel" mogelijk maakt, zonder handmatige export.
#
# Belangrijk om te weten voordat je hierop bouwt:
# - Zonder betaald abonnement krijg je alleen "ongelimiteerd toegang tot een test dataset"
#   van 10.000 willekeurige documenten — GEEN echte, gefilterde resultaten op jouw profiel.
#   Voor echte automatische discovery is het "Small"-abonnement nodig: €15/maand.
# - De exacte filter-veldnaam voor SBI-code en de vorm van de response zijn gebaseerd op
#   de documentatie, niet live geverifieerd — controleer dit bij de eerste echte run.

BASE_URL = "https://api.overheid.io/v3/openkvk"
MAX_RESULTATEN_PER_COMBINATIE = 200  # veiligheidsgrens tegen onbedoeld hoog verbruik


class OpenKvkClient:
    def __init__(self, apikey: str, base_url: str = BASE_URL, timeout: float = 10.0) -> None:
        self.apikey = apikey
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"ovio-api-key": self.apikey})

    def _zoek_pagina(self, sbi_code: str, plaats: str, page: int, size: int = 100) -> dict:
        resp = self.session.get(
            self.base_url,
            params={
                "filters[sbi]": sbi_code,
                "filters[bezoeklocatie.plaats]": plaats,
                "size": size,
                "page": page,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _pak_resultaten(data: dict) -> List[dict]:
        if isinstance(data, list):
            return data
        embedded = data.get("_embedded")
        if isinstance(embedded, dict):
            for waarde in embedded.values():
                if isinstance(waarde, list):
                    return waarde
        for sleutel in ("results", "resultaten", "items"):
            if isinstance(data.get(sleutel), list):
                return data[sleutel]
        return []

    def _naar_company(self, item: dict, sbi_code: str, plaats: str) -> Optional[Company]:
        naam = item.get("naam") or (item.get("huidigeHandelsNamen") or [None])[0]
        if not naam:
            return None
        activiteiten = item.get("activiteiten") or []
        sector_omschrijvingen = [a.get("omschrijving") for a in activiteiten if a.get("omschrijving")]
        bezoeklocatie = item.get("bezoeklocatie") or {}
        bedrijf = Company(
            bedrijfsnaam=naam,
            plaats=bezoeklocatie.get("plaats", plaats),
            postcode=bezoeklocatie.get("postcode"),
            sector_bron="; ".join(sector_omschrijvingen) or None,
            grootte_indicatie=None,
            signalen_bron={},
            bron="openkvk.nl (overheid.io)",
        )
        bedrijf.kvk_nummer = item.get("kvknummer") or item.get("kvkNummer")
        bedrijf.sbi_codes_kvk = item.get("sbi") or [sbi_code]
        bedrijf.sbi_omschrijvingen_kvk = sector_omschrijvingen
        bedrijf.kvk_status = "gevonden via OpenKvK"
        return bedrijf

    def zoek(self, profiel: Profile) -> List[Company]:
        gevonden: Dict[str, Company] = {}

        sbi_codes = profiel.sbi_codes or [None]
        plaatsen = profiel.regio_plaatsen or [None]

        for sbi_code in sbi_codes:
            for plaats in plaatsen:
                pagina = 1
                opgehaald = 0
                while opgehaald < MAX_RESULTATEN_PER_COMBINATIE:
                    data = self._zoek_pagina(sbi_code, plaats, page=pagina, size=100)
                    items = self._pak_resultaten(data)
                    if not items:
                        break
                    for item in items:
                        bedrijf = self._naar_company(item, sbi_code, plaats)
                        if bedrijf is None:
                            continue
                        sleutel = bedrijf.kvk_nummer or f"{bedrijf.bedrijfsnaam}|{bedrijf.plaats}"
                        gevonden.setdefault(sleutel, bedrijf)
                    opgehaald += len(items)
                    if len(items) < 100:
                        break
                    pagina += 1

        return list(gevonden.values())

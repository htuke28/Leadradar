from __future__ import annotations

from typing import Optional

import requests

from ..models import Company

# Publieke, gedeelde testkey van de KvK developer portal (developers.kvk.nl/nl/documentation/testing).
# Werkt alleen tegen de testomgeving met een beperkte, vaste testdataset — NIET gebruiken in productie.
# Verifieer bij het aanvragen van een echte key of dit endpoint/key-formaat nog actueel is.
TEST_APIKEY = "l7xx1f2691f2520d487b902f4e0b57a0b197"
TEST_BASE_URL = "https://api.kvk.nl/test/api"


class KvkClient:
    """Dunne client rond de KvK Zoeken- en Basisprofiel-API.

    Rolverdeling is bewust beperkt: de Zoeken-API kan NIET filteren op SBI-code,
    regio-straal of aantal medewerkers (bevestigd via developers.kvk.nl/nl/support/faq/zoeken-api,
    20-08-2026) — hij zoekt alleen op naam/plaats/postcode/kvknummer. Deze client wordt dus gebruikt
    om een al-gevonden bedrijf (uit de CSV-bron) te verifiëren en te verrijken met officiële
    KvK-gegevens, SBI-activiteiten en medewerkersaantal — niet om bedrijven te ontdekken.
    """

    def __init__(
        self,
        apikey: str = TEST_APIKEY,
        base_url: str = TEST_BASE_URL,
        timeout: float = 8.0,
    ) -> None:
        self.apikey = apikey
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"apikey": self.apikey})

    def zoek_kvk_nummer(self, naam: str, plaats: str) -> Optional[str]:
        resp = self.session.get(
            f"{self.base_url}/v2/zoeken",
            params={"naam": naam, "plaats": plaats, "type": "hoofdvestiging"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        resultaten = resp.json().get("resultaten", [])
        if not resultaten:
            return None
        for r in resultaten:
            if r.get("naam", "").strip().lower() == naam.strip().lower():
                return r.get("kvkNummer")
        return resultaten[0].get("kvkNummer")

    def haal_basisprofiel(self, kvk_nummer: str) -> dict:
        resp = self.session.get(
            f"{self.base_url}/v1/basisprofielen/{kvk_nummer}",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def verrijk(self, bedrijf: Company) -> Company:
        """Vult een Company met officiële KvK-gegevens. Faalt zacht: zet kvk_status,
        gooit nooit door naar de rest van de pipeline zodat één netwerkfout de hele run
        niet stopt."""
        try:
            kvk_nummer = self.zoek_kvk_nummer(bedrijf.bedrijfsnaam, bedrijf.plaats)
            if not kvk_nummer:
                bedrijf.kvk_status = "geen match"
                return bedrijf

            profiel = self.haal_basisprofiel(kvk_nummer)
            hoofdvestiging = profiel.get("hoofdvestiging") or {}
            activiteiten = profiel.get("sbiActiviteiten") or hoofdvestiging.get("sbiActiviteiten") or []

            bedrijf.kvk_nummer = kvk_nummer
            bedrijf.kvk_naam_officieel = profiel.get("naam")
            bedrijf.sbi_codes_kvk = [a.get("sbiCode") for a in activiteiten if a.get("sbiCode")]
            bedrijf.sbi_omschrijvingen_kvk = [
                a.get("sbiOmschrijving") for a in activiteiten if a.get("sbiOmschrijving")
            ]
            bedrijf.medewerkers_kvk = (
                hoofdvestiging.get("totaalWerkzamePersonen")
                or profiel.get("totaalWerkzamePersonen")
            )
            bedrijf.kvk_status = "gevonden"
        except requests.RequestException as exc:
            bedrijf.kvk_status = f"fout: {exc.__class__.__name__}"
        return bedrijf

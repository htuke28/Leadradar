from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

import requests

from ..models import Company

# Verrijkt een gevonden bedrijf met twee dingen die geen van de andere bronnen levert:
# 1. Een concreet signaal ("vacature_elektromonteur") door de eigen vacature-pagina van het
#    bedrijf te doorzoeken op trefwoorden.
# 2. Een best-effort contactpersoon-naam, gevonden op de eigen contact/over-ons-pagina.
#
# Dit is bewust GEEN scraping van een platform van een ander (LinkedIn, Google-resultaten) —
# alleen de eigen, publieke website van het bedrijf zelf, net als een mens dat handmatig zou
# doen. Dat is dezelfde grens die al eerder is aangehouden bij het schrappen van LinkedIn als
# bron (AVG/spelregels, zie bouwbrief punt 6).
#
# Belangrijk om te weten voordat je hierop vertrouwt:
# - Werkt alleen als er al een website-URL bekend is (van Google Places, of van OpenKvK als
#   die het internetadres-veld invult — niet gegarandeerd, zie sources/openkvk_source.py).
# - Dit is een heuristiek, geen garantie: sommige sites blokkeren simpele requests
#   (JavaScript-only content, bot-detectie), en de naam-regex mist mensen met een titel die
#   er niet in staat. Behandel elk gevonden resultaat als "te verifiëren", niet als feit —
#   vandaar de aparte "(ongeverifieerd, via website)"-notitie in de output.
# - Respecteert momenteel geen robots.txt — bij verder opschalen (grote volumes, veel
#   bedrijven per run) verdient dat alsnog aandacht.
# - "geen_eigen_elektrotechnicus" (een afwezigheids-signaal) wordt hier NIET gedetecteerd —
#   je kunt van een website niet betrouwbaar afleiden wat een bedrijf NIET heeft. Dat blijft
#   iets wat Gilbert op de (kortere) shortlist zelf beoordeelt, of dat via een CSV met
#   voorkennis wordt aangeleverd.

VACATURE_PAD_TREFWOORDEN = ["vacature", "vacatures", "werken-bij", "werkenbij", "jobs", "carriere", "carrière"]
CONTACT_PAD_TREFWOORDEN = ["contact", "over-ons", "over_ons", "overons", "team", "wie-zijn-wij"]

FUNCTIETITELS = [
    "algemeen directeur",
    "eigenaar/directeur",
    "directeur",
    "eigenaar",
    "oprichter",
    "contactpersoon",
    "vestigingsmanager",
    "bedrijfsleider",
]

# Grove naam-regex: een functietitel gevolgd door twee (of drie, met tussenvoegsel) woorden
# die als naam gelezen kunnen worden. Bewust eenvoudig gehouden — dit is een heuristiek.
_NAAM_PATROON = re.compile(
    r"(?:" + "|".join(FUNCTIETITELS) + r")\s*[:\-–]?\s*"
    r"([A-ZÀ-Ý][a-zà-ÿ'.]+(?:\s+(?:van|de|der|den|het|te)\b)?\s+[A-ZÀ-Ý][a-zà-ÿ'.]+)",
    re.IGNORECASE,
)


class WebsiteEnricher:
    def __init__(self, timeout: float = 8.0, user_agent: str = "Leadradar/0.1 (+lead-verrijking, best-effort)") -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _fetch(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code >= 400:
                return None
            return resp.text
        except requests.RequestException:
            return None

    @staticmethod
    def _vind_links(html: str, basis_url: str, trefwoorden: List[str]) -> List[str]:
        gevonden = []
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            href = match.group(1)
            if any(t in href.lower() for t in trefwoorden):
                gevonden.append(urljoin(basis_url, href))
        return gevonden

    def _detecteer_vacature_elektromonteur(self, homepage_html: str, basis_url: str) -> bool:
        teksten = [homepage_html]
        for link in self._vind_links(homepage_html, basis_url, VACATURE_PAD_TREFWOORDEN)[:3]:
            pagina = self._fetch(link)
            if pagina:
                teksten.append(pagina)
        volledige_tekst = " ".join(teksten).lower()
        heeft_functie = "elektromonteur" in volledige_tekst
        heeft_vacature_context = any(
            t in volledige_tekst for t in ["vacature", "we zoeken", "wij zoeken", "kom werken", "vacatures"]
        )
        return heeft_functie and heeft_vacature_context

    def _vind_contactpersoon(self, homepage_html: str, basis_url: str) -> Optional[str]:
        teksten = [homepage_html]
        for link in self._vind_links(homepage_html, basis_url, CONTACT_PAD_TREFWOORDEN)[:3]:
            pagina = self._fetch(link)
            if pagina:
                teksten.append(pagina)
        for tekst in teksten:
            zonder_tags = re.sub(r"<[^>]+>", " ", tekst)
            zonder_tags = re.sub(r"\s+", " ", zonder_tags)
            match = _NAAM_PATROON.search(zonder_tags)
            if match:
                return match.group(1).strip()
        return None

    def verrijk(self, bedrijf: Company, gewenste_signalen: Optional[List[str]] = None) -> Company:
        """Zacht falen: als er niets bereikbaar of vindbaar is, blijft het bedrijf verder
        onveranderd (met een status-notitie) — nooit een crash van de hele run door één
        onbereikbare of trage website."""
        if not bedrijf.website:
            bedrijf.website_status = "geen website bekend"
            return bedrijf

        homepage = self._fetch(bedrijf.website)
        if homepage is None:
            bedrijf.website_status = "website niet bereikbaar"
            return bedrijf

        gewenste_signalen = gewenste_signalen or []
        if "vacature_elektromonteur" in gewenste_signalen:
            if self._detecteer_vacature_elektromonteur(homepage, bedrijf.website):
                bedrijf.signalen_bron["vacature_elektromonteur"] = True

        contactpersoon = self._vind_contactpersoon(homepage, bedrijf.website)
        if contactpersoon:
            bedrijf.contactpersoon = contactpersoon
            bedrijf.contactpersoon_bron = "website (ongeverifieerd)"

        bedrijf.website_status = "verwerkt"
        return bedrijf

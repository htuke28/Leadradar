from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

import requests

from ..models import Company

# Verrijkt een gevonden bedrijf met dingen die geen van de andere bronnen levert:
# 1. Een concreet signaal ("vacature_elektromonteur") door de eigen vacature-pagina van het
#    bedrijf te doorzoeken op trefwoorden.
# 2. Een best-effort contactpersoon-naam, e-mailadres en telefoonnummer, gevonden op de eigen
#    contact/over-ons-pagina (mailto:/tel:-links eerst, anders een regex over de platte tekst).
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

_EMAIL_PATROON = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_GEEN_ECHTE_EMAIL_EXTENSIES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico")

# Nederlandse telefoonnummers: 0X-XXXXXXXX (vast/mobiel) of +31X-XXXXXXXX, met optionele
# spaties/streepjes. Bewust eenvoudig gehouden, net als de naam-regex hierboven.
_TELEFOON_PATROON = re.compile(r"(?:\+31[\s\-]?|0)[1-9](?:[\s\-]?\d){8}")


def _vind_email(html: str) -> Optional[str]:
    mailto = re.search(r'href=["\']mailto:([^"\'?]+)', html, re.IGNORECASE)
    if mailto:
        return mailto.group(1).strip()
    zonder_tags = re.sub(r"<[^>]+>", " ", html)
    for match in _EMAIL_PATROON.finditer(zonder_tags):
        kandidaat = match.group(0)
        if kandidaat.lower().endswith(_GEEN_ECHTE_EMAIL_EXTENSIES):
            continue  # bijv. "logo@2x.png" in een class-/bestandsnaam, geen echt e-mailadres
        return kandidaat
    return None


def _vind_telefoonnummer(html: str) -> Optional[str]:
    tel = re.search(r'href=["\']tel:([^"\']+)', html, re.IGNORECASE)
    if tel:
        return tel.group(1).strip()
    zonder_tags = re.sub(r"<[^>]+>", " ", html)
    match = _TELEFOON_PATROON.search(zonder_tags)
    return match.group(0).strip() if match else None


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

    def _vind_contactgegevens(
        self, homepage_html: str, basis_url: str
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Doorzoekt homepage + contact/over-ons-pagina's op naam, e-mail en telefoonnummer.
        Stopt zodra alle drie gevonden zijn; anders wat er wél gevonden is (kan gedeeltelijk)."""
        teksten = [homepage_html]
        for link in self._vind_links(homepage_html, basis_url, CONTACT_PAD_TREFWOORDEN)[:3]:
            pagina = self._fetch(link)
            if pagina:
                teksten.append(pagina)

        naam = email = telefoon = None
        for tekst in teksten:
            if not naam:
                zonder_tags = re.sub(r"<[^>]+>", " ", tekst)
                zonder_tags = re.sub(r"\s+", " ", zonder_tags)
                match = _NAAM_PATROON.search(zonder_tags)
                if match:
                    naam = match.group(1).strip()
            if not email:
                email = _vind_email(tekst)
            if not telefoon:
                telefoon = _vind_telefoonnummer(tekst)
            if naam and email and telefoon:
                break
        return naam, email, telefoon

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

        naam, email, telefoon = self._vind_contactgegevens(homepage, bedrijf.website)
        if naam:
            bedrijf.contactpersoon = naam
            bedrijf.contactpersoon_bron = "website (ongeverifieerd)"
        if email:
            bedrijf.email = email
        if telefoon:
            bedrijf.telefoonnummer = telefoon

        bedrijf.website_status = "verwerkt"
        return bedrijf

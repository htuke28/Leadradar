"""Test de website-verrijkingsstap met gemockte HTTP-responses. Dit sandbox-netwerk kan geen
echte bedrijfswebsites bereiken, dus dit is de haalbare verificatie hier — een live-run moet
vanaf een machine met internettoegang, zie README."""

from unittest.mock import MagicMock, patch

from leadradar.enrich.website import WebsiteEnricher
from leadradar.models import Company


def _mock_response(html: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = html
    return resp


HOMEPAGE_MET_VACATURELINK = """
<html><body>
<nav><a href="/vacatures">Vacatures</a> <a href="/contact">Contact</a></nav>
<p>Welkom bij Twentse Machinefabriek.</p>
</body></html>
"""

VACATURE_PAGINA = """
<html><body>
<h1>Vacature: Elektromonteur</h1>
<p>Wij zoeken een ervaren elektromonteur voor onze werkplaats in Hengelo.</p>
</body></html>
"""

CONTACT_PAGINA = """
<html><body>
<h2>Over ons</h2>
<p>Directeur: Jan Bakker</p>
<p>Bel ons op 074-1234567.</p>
</body></html>
"""


def test_verrijk_vindt_vacature_signaal_en_contactpersoon():
    client = WebsiteEnricher()
    responses = {
        "https://twentsemachinefabriek.nl": _mock_response(HOMEPAGE_MET_VACATURELINK),
        "https://twentsemachinefabriek.nl/vacatures": _mock_response(VACATURE_PAGINA),
        "https://twentsemachinefabriek.nl/contact": _mock_response(CONTACT_PAGINA),
    }

    def _fake_get(url, timeout=None):
        return responses.get(url, _mock_response("", status_code=404))

    with patch.object(client.session, "get", side_effect=_fake_get):
        bedrijf = Company(
            bedrijfsnaam="Twentse Machinefabriek B.V.",
            plaats="Hengelo",
            website="https://twentsemachinefabriek.nl",
        )
        client.verrijk(bedrijf, gewenste_signalen=["vacature_elektromonteur"])

    assert bedrijf.website_status == "verwerkt"
    assert bedrijf.signalen_bron.get("vacature_elektromonteur") is True
    assert bedrijf.contactpersoon == "Jan Bakker"
    assert bedrijf.contactpersoon_bron == "website (ongeverifieerd)"


def test_verrijk_zonder_website_slaat_over():
    client = WebsiteEnricher()
    bedrijf = Company(bedrijfsnaam="Onbekend B.V.", plaats="Nergens", website=None)
    client.verrijk(bedrijf)

    assert bedrijf.website_status == "geen website bekend"
    assert bedrijf.contactpersoon is None


def test_verrijk_bij_onbereikbare_website_stopt_pipeline_niet():
    import requests

    client = WebsiteEnricher()
    with patch.object(client.session, "get", side_effect=requests.ConnectionError("timeout")):
        bedrijf = Company(bedrijfsnaam="Onbereikbaar B.V.", plaats="Nergens", website="https://onbereikbaar.example")
        client.verrijk(bedrijf)

    assert bedrijf.website_status == "website niet bereikbaar"


def test_verrijk_zonder_vacaturepagina_geen_signaal():
    client = WebsiteEnricher()
    responses = {
        "https://stillebakker.nl": _mock_response("<html><body>Wij bakken brood.</body></html>"),
    }

    def _fake_get(url, timeout=None):
        return responses.get(url, _mock_response("", status_code=404))

    with patch.object(client.session, "get", side_effect=_fake_get):
        bedrijf = Company(bedrijfsnaam="Stille Bakker B.V.", plaats="Enschede", website="https://stillebakker.nl")
        client.verrijk(bedrijf, gewenste_signalen=["vacature_elektromonteur"])

    assert bedrijf.signalen_bron.get("vacature_elektromonteur") is not True
    assert bedrijf.contactpersoon is None

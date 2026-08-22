"""Test de Google Places-adapter met gemockte HTTP-responses (veldnamen o.b.v. de
Google-documentatie, geraadpleegd 20-08-2026). Zelfde reden als bij de andere twee
bronnen: dit sandbox-netwerk kan geen live calls maken naar places.googleapis.com."""

from unittest.mock import MagicMock, patch

from leadradar.profile import Profile
from leadradar.sources.google_places_source import GooglePlacesClient


def _profiel() -> Profile:
    return Profile(
        naam="test",
        sectoren=["Elektrotechnisch installatiebedrijf"],
        sbi_codes=[],
        grootte_min=0,
        grootte_max=10_000,
        regio_omschrijving="Twente",
        regio_plaatsen=["Hengelo"],
        type="eindklant",
        signalen=[],
        gewichten={"sector": 30, "grootte": 20, "regio": 20, "signaal": 30},
    )


def _mock_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json.return_value = payload
    return resp


def test_zoek_vindt_bedrijven_en_stopt_zonder_nextpagetoken():
    client = GooglePlacesClient(apikey="testkey")
    pagina = _mock_response(
        {
            "places": [
                {
                    "id": "places/abc123",
                    "displayName": {"text": "Twentse Elektrotechniek B.V."},
                    "formattedAddress": "Hengelosestraat 1, 7550 AB Hengelo",
                    "websiteUri": "https://twentse-elektrotechniek-voorbeeld.nl",
                    "types": ["electrician", "point_of_interest"],
                }
            ]
        }
    )

    with patch.object(client.session, "post", return_value=pagina):
        bedrijven = client.zoek(_profiel())

    assert len(bedrijven) == 1
    assert bedrijven[0].bedrijfsnaam == "Twentse Elektrotechniek B.V."
    assert bedrijven[0].bron == "Google Places"
    assert bedrijven[0].grootte_indicatie is None  # eerlijk: ook deze bron levert geen grootte


def test_zoek_dedupliceert_op_place_id():
    client = GooglePlacesClient(apikey="testkey")
    item = {
        "id": "places/dezelfde",
        "displayName": {"text": "Dubbel B.V."},
        "types": ["electrician"],
    }
    profiel = _profiel()
    profiel.sectoren = ["Elektricien", "Installatiebedrijf"]  # kan hetzelfde bedrijf 2x opleveren

    pagina = _mock_response({"places": [item]})

    with patch.object(client.session, "post", return_value=pagina):
        bedrijven = client.zoek(profiel)

    assert len(bedrijven) == 1


def test_zoek_zonder_plaatsen_levert_niets_op_en_crasht_niet():
    client = GooglePlacesClient(apikey="testkey")
    profiel = _profiel()
    profiel.regio_plaatsen = []

    with patch.object(client.session, "post") as mock_post:
        bedrijven = client.zoek(profiel)

    mock_post.assert_not_called()
    assert bedrijven == []

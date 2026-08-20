"""Test de KvK-adapter met gemockte HTTP-responses (veldnamen o.b.v. de officiële
developers.kvk.nl-documentatie, geraadpleegd 20-08-2026). Dit sandbox-netwerk staat
geen uitgaande calls naar api.kvk.nl toe, dus dit is de haalbare verificatie hier —
een live-run moet vanaf een machine met internettoegang, zie README."""

from unittest.mock import MagicMock, patch

from leadradar.enrich.kvk import KvkClient
from leadradar.models import Company


def _mock_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json.return_value = payload
    return resp


def test_verrijk_vindt_bedrijf_en_vult_kvk_gegevens_aan():
    client = KvkClient()
    zoek_resp = _mock_response(
        {"resultaten": [{"kvkNummer": "68750110", "naam": "Twentse Machinefabriek B.V."}]}
    )
    profiel_resp = _mock_response(
        {
            "naam": "Twentse Machinefabriek B.V.",
            "sbiActiviteiten": [
                {"sbiCode": "2822", "sbiOmschrijving": "Machinebouw", "indHoofdactiviteit": "Ja"}
            ],
            "hoofdvestiging": {"totaalWerkzamePersonen": 38},
        }
    )

    with patch.object(client.session, "get", side_effect=[zoek_resp, profiel_resp]):
        bedrijf = Company(bedrijfsnaam="Twentse Machinefabriek B.V.", plaats="Hengelo")
        client.verrijk(bedrijf)

    assert bedrijf.kvk_status == "gevonden"
    assert bedrijf.kvk_nummer == "68750110"
    assert bedrijf.medewerkers_kvk == 38
    assert "2822" in bedrijf.sbi_codes_kvk


def test_verrijk_zonder_resultaat_markeert_geen_match():
    client = KvkClient()
    zoek_resp = _mock_response({"resultaten": []})

    with patch.object(client.session, "get", return_value=zoek_resp):
        bedrijf = Company(bedrijfsnaam="Onbekende Firma", plaats="Nergens")
        client.verrijk(bedrijf)

    assert bedrijf.kvk_status == "geen match"
    assert bedrijf.kvk_nummer is None


def test_verrijk_bij_netwerkfout_stopt_pipeline_niet():
    import requests

    client = KvkClient()
    with patch.object(client.session, "get", side_effect=requests.ConnectionError("geen netwerk")):
        bedrijf = Company(bedrijfsnaam="Wat Dan Ook B.V.", plaats="Hengelo")
        client.verrijk(bedrijf)

    assert bedrijf.kvk_status.startswith("fout:")

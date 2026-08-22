"""Test de OpenKvK-adapter met gemockte HTTP-responses (veldnamen o.b.v. de
overheid.io-documentatie, geraadpleegd 20-08-2026). Zelfde reden als bij de KvK-adapter:
dit sandbox-netwerk kan geen live calls maken naar api.overheid.io."""

from unittest.mock import MagicMock, patch

from leadradar.profile import Profile
from leadradar.sources.openkvk_source import OpenKvkClient


def _profiel() -> Profile:
    return Profile(
        naam="test",
        sectoren=["Machinebouw"],
        sbi_codes=["2822"],
        grootte_min=10,
        grootte_max=100,
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


def test_zoek_vindt_bedrijven_en_stopt_na_lege_pagina():
    client = OpenKvkClient(apikey="testkey")
    pagina_1 = _mock_response(
        {
            "_embedded": {
                "openkvk": [
                    {
                        "kvknummer": "68750110",
                        "naam": "Twentse Machinefabriek B.V.",
                        "bezoeklocatie": {"plaats": "Hengelo", "postcode": "7550AB"},
                        "sbi": ["2822"],
                        "activiteiten": [{"code": "2822", "omschrijving": "Machinebouw", "hoofdactiviteit": True}],
                    }
                ]
            }
        }
    )
    pagina_2 = _mock_response({"_embedded": {"openkvk": []}})

    with patch.object(client.session, "get", side_effect=[pagina_1, pagina_2]):
        bedrijven = client.zoek(_profiel())

    assert len(bedrijven) == 1
    assert bedrijven[0].bedrijfsnaam == "Twentse Machinefabriek B.V."
    assert bedrijven[0].kvk_nummer == "68750110"
    assert bedrijven[0].bron == "openkvk.nl (overheid.io)"
    assert bedrijven[0].grootte_indicatie is None  # eerlijk: deze bron levert geen grootte


def test_zoek_dedupliceert_op_kvknummer():
    client = OpenKvkClient(apikey="testkey")
    item = {
        "kvknummer": "68750110",
        "naam": "Dubbel B.V.",
        "bezoeklocatie": {"plaats": "Hengelo"},
        "sbi": ["2822"],
        "activiteiten": [],
    }
    profiel = _profiel()
    profiel.regio_plaatsen = ["Hengelo", "Almelo"]  # zelfde bedrijf kan in twee zoekopdrachten voorkomen

    pagina_leeg = _mock_response({"_embedded": {"openkvk": []}})
    pagina_met_item = _mock_response({"_embedded": {"openkvk": [item]}})

    with patch.object(
        client.session, "get",
        side_effect=[pagina_met_item, pagina_leeg, pagina_met_item, pagina_leeg],
    ):
        bedrijven = client.zoek(profiel)

    assert len(bedrijven) == 1

from leadradar.models import Company
from leadradar.profile import Profile
from leadradar.scoring import score_bedrijf


def _profiel() -> Profile:
    return Profile(
        naam="test",
        sectoren=["Machinebouw"],
        sbi_codes=["2822"],
        grootte_min=10,
        grootte_max=100,
        regio_omschrijving="Twente",
        type="eindklant",
        signalen=["vacature_elektromonteur", "geen_eigen_elektrotechnicus"],
        gewichten={"sector": 30, "grootte": 20, "regio": 20, "signaal": 30},
    )


def test_volledige_match_geeft_maximale_score():
    profiel = _profiel()
    bedrijf = Company(
        bedrijfsnaam="Test B.V.",
        plaats="Hengelo",
        sector_bron="Machinebouw",
        grootte_indicatie=40,
        signalen_bron={"vacature_elektromonteur": True, "geen_eigen_elektrotechnicus": True},
    )
    bedrijf.sbi_codes_kvk = ["2822"]
    bedrijf.medewerkers_kvk = 40

    score_bedrijf(bedrijf, profiel)

    assert bedrijf.score == 100.0
    assert "sector komt overeen" in bedrijf.match_redenen
    assert any("grootte binnen" in r for r in bedrijf.match_redenen)


def test_geen_sector_of_signaal_match_geeft_lage_score():
    profiel = _profiel()
    bedrijf = Company(
        bedrijfsnaam="Ander B.V.",
        plaats="Groningen",
        sector_bron="Bakkerijmachines",
        grootte_indicatie=480,
        signalen_bron={},
    )

    score_bedrijf(bedrijf, profiel)

    # alleen het regio-gewicht (voorgefilterd bij de bron) telt nog mee
    assert bedrijf.score == 20.0
    assert "sector komt overeen" not in bedrijf.match_redenen


def test_onbekende_grootte_wordt_als_onbevestigd_gemarkeerd_niet_als_mismatch():
    profiel = _profiel()
    bedrijf = Company(
        bedrijfsnaam="Zonder Groottedata B.V.",
        plaats="Hengelo",
        sector_bron="Machinebouw",
        grootte_indicatie=None,
        signalen_bron={},
    )

    score_bedrijf(bedrijf, profiel)

    assert "grootte onbevestigd" in bedrijf.match_redenen

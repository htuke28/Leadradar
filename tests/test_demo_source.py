from leadradar.profile import Profile
from leadradar.sources.demo_source import DemoClient


def _profiel() -> Profile:
    return Profile(
        naam="Test",
        sectoren=["Machinebouw"],
        sbi_codes=["2829"],
        grootte_min=10,
        grootte_max=100,
        regio_omschrijving="Twente",
        regio_plaatsen=["Hengelo", "Almelo"],
        type="eindklant",
        signalen=["vacature_elektromonteur", "geen_eigen_elektrotechnicus"],
    )


def test_demo_client_levert_bedrijven_binnen_het_profiel_op():
    bedrijven = DemoClient().zoek(_profiel())

    assert len(bedrijven) > 0
    for b in bedrijven:
        assert b.plaats in {"Hengelo", "Almelo"}
        assert b.sector_bron == "Machinebouw"
        assert "demo" in b.bron


def test_demo_client_geeft_variatie_in_grootte_voor_scoring():
    bedrijven = DemoClient().zoek(_profiel())
    groottes = {b.grootte_indicatie for b in bedrijven}

    # Zowel bedrijven binnen als (ruim) buiten grootte_min/max, anders is er niks te filteren.
    assert any(10 <= g <= 100 for g in groottes)
    assert any(g > 100 for g in groottes)


def test_demo_client_valt_terug_op_standaardplaatsen_zonder_profielregio():
    profiel = Profile(
        naam="Zonder regio",
        sectoren=[],
        sbi_codes=[],
        grootte_min=0,
        grootte_max=1000,
        regio_omschrijving="",
        regio_plaatsen=[],
        type="eindklant",
        signalen=[],
    )

    bedrijven = DemoClient().zoek(profiel)

    assert len(bedrijven) > 0
    assert all(b.plaats for b in bedrijven)

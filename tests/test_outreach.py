from leadradar.models import Company
from leadradar.outreach import genereer_bericht
from leadradar.profile import Profile


def _profiel(**overrides) -> Profile:
    basis = dict(
        naam="Test",
        sectoren=["Algemene machinebouw"],
        sbi_codes=["2822"],
        grootte_min=10,
        grootte_max=100,
        regio_omschrijving="Twente",
        regio_plaatsen=["Hengelo"],
        type="eindklant",
        signalen=["vacature_elektromonteur", "geen_eigen_elektrotechnicus"],
    )
    basis.update(overrides)
    return Profile(**basis)


def test_bericht_met_contactpersoon_en_signaal():
    profiel = _profiel()
    bedrijf = Company(
        bedrijfsnaam="Twentse Machinefabriek B.V.",
        plaats="Hengelo",
        sector_bron="Machinebouw",
        contactpersoon="Jan Bakker",
        signalen_bron={"vacature_elektromonteur": True},
    )
    bericht = genereer_bericht(bedrijf, profiel)

    assert "Jan Bakker" in bericht
    assert "Twentse Machinefabriek B.V." in bericht
    assert "vacature_elektromonteur" in bericht


def test_bericht_zonder_contactpersoon_of_signaal_blijft_bruikbaar():
    profiel = _profiel()
    bedrijf = Company(bedrijfsnaam="Onbekende Firma B.V.", plaats="Hengelo")
    bericht = genereer_bericht(bedrijf, profiel)

    assert "Hoi daar," in bericht
    assert "Onbekende Firma B.V." in bericht
    # Geen kapotte placeholder als er geen signaal is:
    assert "{signaal_zin}" not in bericht

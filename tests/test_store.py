from leadradar.models import Company
from leadradar.store import LeadStore, row_naar_company


def _bedrijf(naam="Testbedrijf B.V.", plaats="Hengelo", score=80.0) -> Company:
    return Company(
        bedrijfsnaam=naam,
        plaats=plaats,
        score=score,
        match_redenen=["sector match", "regio match"],
        bron="test",
    )


def test_upsert_en_ophalen_geeft_bedrijf_terug(tmp_path):
    store = LeadStore(tmp_path / "leads.db")
    store.upsert_bedrijven([_bedrijf()], profiel_naam="Profiel A")

    leads = store.haal_leads(profiel_naam="Profiel A")

    assert len(leads) == 1
    assert leads[0]["bedrijfsnaam"] == "Testbedrijf B.V."
    assert leads[0]["status"] == "nieuw"


def test_status_blijft_behouden_bij_hernieuwde_upsert(tmp_path):
    store = LeadStore(tmp_path / "leads.db")
    store.upsert_bedrijven([_bedrijf(score=60.0)], profiel_naam="Profiel A")
    [lead] = store.haal_leads(profiel_naam="Profiel A")
    store.zet_status(lead["id"], "interessant")

    # Zelfde bedrijf komt opnieuw binnen met een bijgewerkte score (bijv. na herverrijking).
    store.upsert_bedrijven([_bedrijf(score=95.0)], profiel_naam="Profiel A")

    [lead_na] = store.haal_leads(profiel_naam="Profiel A")
    assert lead_na["status"] == "interessant"
    assert lead_na["score"] == 95.0


def test_filter_op_status_sluit_niet_interessant_uit(tmp_path):
    store = LeadStore(tmp_path / "leads.db")
    store.upsert_bedrijven(
        [_bedrijf("Bedrijf A", "Almelo"), _bedrijf("Bedrijf B", "Borne")],
        profiel_naam="Profiel A",
    )
    leads = store.haal_leads(profiel_naam="Profiel A")
    afgewezen = next(r for r in leads if r["bedrijfsnaam"] == "Bedrijf B")
    store.zet_status(afgewezen["id"], "niet interessant")

    overgebleven = store.haal_leads(
        profiel_naam="Profiel A", statussen=["nieuw", "interessant", "contact gelegd", "klant"]
    )

    assert [r["bedrijfsnaam"] for r in overgebleven] == ["Bedrijf A"]


def test_verwijderen_haalt_lead_definitief_weg(tmp_path):
    store = LeadStore(tmp_path / "leads.db")
    store.upsert_bedrijven([_bedrijf()], profiel_naam="Profiel A")
    [lead] = store.haal_leads(profiel_naam="Profiel A")

    store.verwijder([lead["id"]])

    assert store.haal_leads(profiel_naam="Profiel A") == []


def test_row_naar_company_zet_velden_correct_terug(tmp_path):
    store = LeadStore(tmp_path / "leads.db")
    store.upsert_bedrijven([_bedrijf()], profiel_naam="Profiel A")
    [row] = store.haal_leads(profiel_naam="Profiel A")

    bedrijf = row_naar_company(row)

    assert bedrijf.bedrijfsnaam == "Testbedrijf B.V."
    assert bedrijf.match_redenen == ["sector match", "regio match"]

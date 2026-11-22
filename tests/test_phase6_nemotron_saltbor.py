"""Pruebas de integración real de Nemotron SV y adaptador E7 con IKarosUnic/sv-people."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agrosv.api import app
from agrosv.social import governance as SG
from agrosv.social import saltbor_adapter
from agrosv.social.nemotron import (
    NemotronDatasetClient,
    is_agricultural_occupation,
    map_occupation_to_archetype,
)
from agrosv.social.persona import AgriculturalPersonaEngine
from agrosv.social.population import AgriculturalPopulationEngine
from agrosv.socio.integration import SocioAgriculturalIntegrationEngine
from agrosv.socio.scenario import AgriculturalScenarioEngine

COFFEE_POINT = {"lat": 13.85, "lon": -89.45}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# --- Nemotron real ----------------------------------------------------------
def test_agricultural_occupation_classifier_rejects_retail():
    assert is_agricultural_occupation(
        "Cultivo de cereales (excepto arroz), legumbres y semillas oleaginosas"
    ) is True
    assert is_agricultural_occupation(
        "Cultivo de plantas con las que se preparan bebidas"
    ) is True
    assert is_agricultural_occupation(
        "Venta al por menor en comercios no especializados con predominio de la venta de alimentos, bebidas o tabaco"
    ) is False
    assert is_agricultural_occupation(
        "Elaboración de bebidas no alcohólicas; producción de aguas minerales y otras aguas embotelladas"
    ) is False


def test_nemotron_corpus_has_real_agricultural_rows_and_passes_separation():
    client_ds = NemotronDatasetClient()
    res = client_ds.query_profiles(limit=25)
    assert res["count"] == 25
    assert res["agricultural_count"] == 25
    assert res["retrieval_mode"] == "local_nemotron_corpus"
    for item in res["profiles"]:
        p = item["profile"]
        assert p["origin"] == "nemotron_dataset"
        assert p["from_nemotron_dataset"] is True
        assert p["agricultural_occupation"] is True
        assert p["uuid"]
        assert p["department"]
    check = SG.check_separation(res["records"])
    assert check["valid"] is True
    assert check["layers"] == {"SOURCE_PROFILE": 25}


def test_nemotron_filter_by_department_and_archetype():
    persona = AgriculturalPersonaEngine()
    coffee = persona.nemotron_agricultural_profiles(
        archetype="coffee_smallholder", limit=10
    )
    assert coffee["count"] >= 5
    for item in coffee["profiles"]:
        assert item["mapped_archetype"] == "coffee_smallholder"
        assert (
            "bebidas" in item["profile"]["occupation"].lower()
            or "caf" in item["profile"]["occupation"].lower()
        )


def test_persona_compose_with_nemotron_corpus_is_consistent():
    pop = AgriculturalPopulationEngine().generate(2, seed=10)["result"]["agents"]
    composed = AgriculturalPersonaEngine().compose(pop[0], use_nemotron_corpus=True)
    assert composed["attachable"] is True
    assert composed["persona"]["role_consistent_with_source"] is True
    assert composed["persona"]["source_profile"]["origin"] == "nemotron_dataset"
    assert composed["persona"]["source_profile"]["from_nemotron_dataset"] is True


def test_generate_from_nemotron_is_reproducible_and_separated():
    pop_engine = AgriculturalPopulationEngine()
    first = pop_engine.generate_from_nemotron(12, seed=9)
    second = pop_engine.generate_from_nemotron(12, seed=9)
    assert first["result"]["nemotron_backed"] is True
    assert first["result"]["unique_nemotron_uuids"] == 12
    assert [a["nemotron_uuid"] for a in first["result"]["agents"]] == [
        a["nemotron_uuid"] for a in second["result"]["agents"]
    ]
    records = []
    for agent in first["result"]["agents"]:
        records.append(agent["source_profile"]["record"])
        records.append(agent["state"])
    check = SG.check_separation(records)
    assert check["valid"] is True
    assert check["layers"] == {
        "SOURCE_PROFILE": 12,
        "SYNTHETIC_AGRICULTURAL_STATE": 12,
    }


def test_socio_integration_and_scenario_preserve_nemotron_source():
    agent = AgriculturalPopulationEngine().generate_from_nemotron(1, seed=4)[
        "result"
    ]["agents"][0]
    profile = SocioAgriculturalIntegrationEngine().profile(
        lon=COFFEE_POINT["lon"],
        lat=COFFEE_POINT["lat"],
        crop_id="coffee",
        agent=agent,
        seed=4,
    )
    human = profile["result"]["human"]
    assert human["nemotron_backed"] is True
    assert human["nemotron_uuid"] == agent["nemotron_uuid"]
    assert human["persona"]["role_consistent_with_source"] is True

    scen = AgriculturalScenarioEngine().run(
        "A_drought",
        lon=COFFEE_POINT["lon"],
        lat=COFFEE_POINT["lat"],
        size=6,
        seed=4,
        population_source="nemotron",
    )
    assert scen["result"]["population"]["population_source"] == "nemotron"
    assert scen["result"]["population"]["nemotron_backed"] is True
    assert scen["layer_check"]["valid"] is True


def test_nemotron_live_fetch_parses_hf_response(monkeypatch):
    class _DummyResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "num_rows_total": 148000,
                "rows": [
                    {
                        "row_idx": 10,
                        "row": {
                            "uuid": "live-uuid-1",
                            "age": 41,
                            "sex": "Femenino",
                            "education_level": "primaria",
                            "occupation": "Cultivo de cereales (excepto arroz), legumbres y semillas oleaginosas",
                            "area": "rural",
                            "department": "Morazán",
                            "municipality": "Morazán Norte",
                            "household_type": "nuclear",
                            "marital_status": "casado",
                        },
                    },
                    {
                        "row_idx": 11,
                        "row": {
                            "uuid": "live-uuid-2",
                            "age": 28,
                            "sex": "Masculino",
                            "education_level": "universitario",
                            "occupation": "Actividades de contabilidad",
                            "area": "urbano",
                            "department": "San Salvador",
                            "municipality": "San Salvador Centro",
                            "household_type": "unipersonal",
                            "marital_status": "soltero",
                        },
                    },
                ],
            }

    monkeypatch.setattr("agrosv.social.nemotron.requests.get", lambda *a, **kw: _DummyResp())
    res = NemotronDatasetClient().query_profiles(live=True, limit=10)
    assert res["retrieval_mode"] == "huggingface_live"
    assert res["count"] == 1
    assert res["profiles"][0]["profile"]["uuid"] == "live-uuid-1"
    assert res["profiles"][0]["mapped_archetype"] == "subsistence_maize"


# --- Adaptador E7 Saltbor (sv-people) ---------------------------------------
def test_saltbor_export_and_roundtrip_import():
    agents = AgriculturalPopulationEngine().generate_from_nemotron(5, seed=3)[
        "result"
    ]["agents"]
    bundle = saltbor_adapter.to_saltbor_bundle(agents, scenario_id="A_drought")
    assert bundle["contract_version"] == "1.0.0"
    assert bundle["direction"] == "agrosv_to_saltbor"
    assert bundle["count"] == 5
    assert bundle["nemotron_backed_count"] == 5
    assert bundle["layer_check"]["valid"] is True

    for prof, plot, ag in zip(bundle["profiles"], bundle["farm_plots"], agents):
        assert prof["data_source"] == "nemotron_dataset"
        assert prof["gender"] in {"male", "female", "non_binary"}
        assert prof["agrosv_agent_id"] == ag["agent_id"]
        assert plot["owner_id"] == ag["agent_id"]
        expected_mz = round(ag["state"]["payload"]["area_ha"] / 0.70, 3)
        assert plot["area_manzanas"] == pytest.approx(expected_mz)

    reimported = saltbor_adapter.from_saltbor_payload({
        "profiles": bundle["profiles"],
        "farm_plots": bundle["farm_plots"],
    })
    assert reimported["count"] == 5
    assert reimported["nemotron_backed_count"] == 5
    assert reimported["layer_check"]["valid"] is True
    assert reimported["agents"][0]["source_profile"]["profile"]["origin"] == "saltbor_adapter"


def test_api_nemotron_and_saltbor_endpoints(client):
    r_ag = client.get("/api/social/nemotron/agricultural?limit=5")
    assert r_ag.status_code == 200
    assert r_ag.json()["count"] == 5

    r_pop = client.post("/api/social/nemotron/population", json={"size": 4, "seed": 2})
    assert r_pop.status_code == 200
    assert r_pop.json()["result"]["nemotron_backed"] is True

    r_contract = client.get("/api/social/saltbor/contract")
    assert r_contract.status_code == 200
    assert "sv-people" in r_contract.json()["target_repo"]

    r_exp = client.post(
        "/api/social/saltbor/export",
        json={"size": 3, "seed": 2, "population_source": "nemotron"},
    )
    assert r_exp.status_code == 200
    exported = r_exp.json()
    assert exported["nemotron_backed_count"] == 3

    r_imp = client.post(
        "/api/social/saltbor/import",
        json={
            "profiles": exported["profiles"],
            "farm_plots": exported["farm_plots"],
            "evaluate_suitability": True,
            "lat": COFFEE_POINT["lat"],
            "lon": COFFEE_POINT["lon"],
        },
    )
    assert r_imp.status_code == 200
    imported = r_imp.json()
    assert imported["count"] == 3
    assert len(imported["agronomic_evaluations"]) == 3
    assert imported["layer_check"]["valid"] is True

    r_socio = client.post(
        "/api/socio/scenario",
        json={
            "scenario_id": "A_drought",
            "lat": COFFEE_POINT["lat"],
            "lon": COFFEE_POINT["lon"],
            "size": 4,
            "seed": 2,
            "population_source": "nemotron",
        },
    )
    assert r_socio.status_code == 200
    assert r_socio.json()["result"]["population"]["nemotron_backed"] is True

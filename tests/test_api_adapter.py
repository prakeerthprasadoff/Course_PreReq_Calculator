from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    payload = r.json()
    assert payload["ok"] is True
    assert "azure_available" in payload


def test_courses_endpoint():
    r = client.get("/courses")
    assert r.status_code == 200
    payload = r.json()
    assert payload["courses"]
    assert payload["graduation_terms"]
    assert payload["start_term_default"]


def test_plan_endpoint_and_followup_endpoints():
    request = {
        "completed_courses": [
            "COMP_SCI 150",
            "COMP_SCI 211",
            "COMP_SCI 213",
            "COMP_SCI 214",
            "COMP_SCI 262",
            "COMP_SCI 335-0",
            "COMP_SCI 336-0",
            "COMP_SCI 340-0",
            "COMP_SCI 343-0",
            "COMP_SCI 349-0",
            "COMP_SCI 311-0",
            "COMP_SCI 312-0",
            "COMP_SCI 321",
            "COMP_SCI 322-0",
            "COMP_SCI 330-0",
        ],
        "desired_courses": ["COMP_SCI 308"],
        "start_term": "Spring 2026",
        "graduation_term": "Spring 2027",
    }
    plan_res = client.post("/plan/generate", json=request)
    assert plan_res.status_code == 200
    plan_payload = plan_res.json()
    assert "feasible" in plan_payload
    assert "routes" in plan_payload

    routes = plan_payload["routes"][:1]
    if routes:
        rec_res = client.post(
            "/tracks/recommend",
            json={
                "completed_courses": request["completed_courses"],
                "desired_courses": request["desired_courses"],
                "graduation_term": request["graduation_term"],
                "routes": routes,
            },
        )
        assert rec_res.status_code == 200
        rec_payload = rec_res.json()
        assert "track_options" in rec_payload

        chosen_track = rec_payload["recommended_track"] or (
            rec_payload["track_options"][0]["track"] if rec_payload["track_options"] else "Systems"
        )
        fin_res = client.post(
            "/tracks/finalize",
            json={"selected_track": chosen_track, "routes": routes, "route_hint": 1},
        )
        assert fin_res.status_code == 200
        fin_payload = fin_res.json()
        assert "final_plan_markdown" in fin_payload

        graph_res = client.post(
            "/graph/route",
            json={
                "route": routes[0],
                "completed_courses": request["completed_courses"],
                "desired_courses": request["desired_courses"],
            },
        )
        assert graph_res.status_code == 200
        graph_payload = graph_res.json()
        assert "dot" in graph_payload

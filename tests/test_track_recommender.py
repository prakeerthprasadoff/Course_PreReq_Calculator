from pathlib import Path

from planner_engine import PlannerEngine
from track_recommender import (
    build_track_payload,
    derive_tracks_from_engine,
    generate_final_track_plan,
    recommend_tracks,
    validate_final_plan_courses,
)


def _fixture_engine(tmp_path: Path) -> PlannerEngine:
    csv_content = """Course,Course Title,Fall 2025,Winter 2026,Spring 2026,Summer 2026,Extracted_Link,Prerequisites,Course Type
COMP_SCI 150,Fundamentals,X,,,,"","",Core Requirement
COMP_SCI 211,Prog II,,X,,,"","COMP_SCI 150",Core Requirement
COMP_SCI 214,DSA,X,X,X,,"","COMP_SCI 211",Core Requirement
COMP_SCI 340,Networking,X,,X,,"","COMP_SCI 214","Breadth: Systems, Technical Elective"
COMP_SCI 349,Machine Learning,,,X,,"","COMP_SCI 214","Breadth: Artificial Intelligence, Technical Elective"
COMP_SCI 336,Algorithms,X,,,,"","COMP_SCI 214","Breadth: Theory, Technical Elective"
"""
    md_content = """5 required courses -
COMP_SCI 150-0
COMP_SCI 211-0
COMP_SCI 213-0
COMP_SCI 214-0
COMP_SCI 262-0
or IEMS 201-0

5 breadth courses chosen from the options below -
Theory
COMP_SCI 336-0
Systems
COMP_SCI 340-0
Artificial Intelligence
COMP_SCI 349-0

Project Courses
Majors must take two courses from this list -
COMP_SCI 340-0

Technical electives
Majors must take six technical electives.
COMP_SCI 340-0
COMP_SCI 349-0
COMP_SCI 336-0
"""
    csv_path = tmp_path / "courses.csv"
    md_path = tmp_path / "degree.md"
    csv_path.write_text(csv_content, encoding="utf-8")
    md_path.write_text(md_content, encoding="utf-8")
    return PlannerEngine(str(csv_path), str(md_path))


class _FakeUnavailableClient:
    available = False


class _FakeBadClient:
    available = True

    def chat_json(self, *args, **kwargs):
        raise RuntimeError("No service")


class _FakeGoodClient:
    available = True

    def chat_json(self, *args, **kwargs):
        return {
            "track_options": [
                {
                    "track": "AI",
                    "rationale": "Most ML electives available.",
                    "aligned_route_index": 1,
                    "confidence": 0.9,
                }
            ],
            "recommended_track": "AI",
            "notes": "Mock response",
        }


def test_derive_tracks_from_course_types(tmp_path: Path):
    engine = _fixture_engine(tmp_path)
    track_to_courses, course_to_tracks = derive_tracks_from_engine(engine)
    assert "Systems" in track_to_courses
    assert "AI" in track_to_courses
    assert "COMP_SCI 340" in track_to_courses["Systems"]
    assert "Systems" in course_to_tracks["COMP_SCI 340"]


def test_recommend_tracks_fallback_and_payload(tmp_path: Path):
    engine = _fixture_engine(tmp_path)
    track_to_courses, _ = derive_tracks_from_engine(engine)
    routes = [{"Fall 2025": ["COMP_SCI 214"], "Winter 2026": ["COMP_SCI 340"]}]
    payload = build_track_payload(
        completed_courses=["COMP_SCI 150", "COMP_SCI 211"],
        desired_courses=["COMP_SCI 340"],
        graduation_term="Spring 2026",
        routes=routes,
        track_to_courses=track_to_courses,
    )
    rec_fallback = recommend_tracks(_FakeUnavailableClient(), payload)
    assert rec_fallback.track_options

    rec_error_fallback = recommend_tracks(_FakeBadClient(), payload)
    assert rec_error_fallback.track_options

    rec_llm = recommend_tracks(_FakeGoodClient(), payload)
    assert rec_llm.recommended_track == "AI"


def test_final_plan_guardrails(tmp_path: Path):
    _ = _fixture_engine(tmp_path)
    routes = [{"Fall 2025": ["COMP_SCI 214"], "Winter 2026": ["COMP_SCI 340"]}]
    assert validate_final_plan_courses(["COMP_SCI 214", "COMP_SCI 340"], routes)
    assert not validate_final_plan_courses(["COMP_SCI 999"], routes)

    final_plan = generate_final_track_plan(
        llm_client=_FakeUnavailableClient(),
        selected_track="Systems",
        feasible_routes=routes,
        route_hint=1,
    )
    assert "Systems" in final_plan.final_plan_markdown
    assert final_plan.courses_referenced

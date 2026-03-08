from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Set

from azure_llm_client import AzureLLMClient, load_azure_llm_config
from planner_engine import PlannerEngine, rule_courses, term_sort_key
from track_recommender import (
    build_track_payload,
    derive_tracks_from_engine,
    generate_final_track_plan,
    recommendation_to_dict,
    recommend_tracks,
)


BASE_DIR = Path(__file__).resolve().parents[1]
COURSE_CSV = str(BASE_DIR / "main_course_info_typed.csv")
DEGREE_MD = str(BASE_DIR / "BS_Mccormick_CS.md")

ENGINE = PlannerEngine(COURSE_CSV, DEGREE_MD)
TRACK_TO_COURSES, _ = derive_tracks_from_engine(ENGINE)
LLM_CLIENT = AzureLLMClient(load_azure_llm_config())


def generate_plan(
    completed_courses: List[str],
    desired_courses: List[str],
    start_term: str,
    graduation_term: str,
):
    return ENGINE.plan(
        completed_courses=completed_courses,
        target_courses=desired_courses,
        start_term=start_term,
        graduation_term=graduation_term,
    )


def plan_to_dict(plan_result) -> Dict:
    return {
        "feasible": plan_result.feasible,
        "message": plan_result.message,
        "routes": plan_result.routes,
        "blockers": plan_result.blockers,
        "alternatives": plan_result.alternatives,
        "degree_audit": asdict(plan_result.degree_audit),
    }


def recommend_tracks_for_routes(
    completed_courses: List[str],
    desired_courses: List[str],
    graduation_term: str,
    routes: List[Dict[str, List[str]]],
) -> Dict:
    payload = build_track_payload(
        completed_courses=completed_courses,
        desired_courses=desired_courses,
        graduation_term=graduation_term,
        routes=routes,
        track_to_courses=TRACK_TO_COURSES,
    )
    rec = recommend_tracks(LLM_CLIENT, payload)
    out = recommendation_to_dict(rec)
    out["azure_available"] = LLM_CLIENT.available
    out["deterministic_fallback_used"] = "fallback" in out.get("notes", "").lower()
    return out


def finalize_track_plan(selected_track: str, routes: List[Dict[str, List[str]]], route_hint: int = 1) -> Dict:
    final_plan = generate_final_track_plan(
        llm_client=LLM_CLIENT,
        selected_track=selected_track,
        feasible_routes=routes,
        route_hint=route_hint,
    )
    out = asdict(final_plan)
    out["azure_available"] = LLM_CLIENT.available
    out["deterministic_fallback_used"] = "fallback" in out.get("notes", "").lower()
    return out


def build_route_graph_dot(
    route: Dict[str, List[str]],
    completed_courses: Set[str],
    desired_courses: Set[str],
) -> str:
    route_courses: Set[str] = set()
    for courses in route.values():
        route_courses.update(courses)

    lines: List[str] = [
        "digraph CoursePlan {",
        'rankdir="LR";',
        'bgcolor="transparent";',
        'node [shape=box, style="rounded,filled", fillcolor="#f5faf7", color="#4a8b5f", fontname="Helvetica"];',
        'edge [color="#7ba88c"];',
    ]

    for course in sorted(route_courses):
        course_fill = "#fff4d6" if course in desired_courses else "#f5faf7"
        lines.append(f'"{course}" [label="{course}", fillcolor="{course_fill}"];')

    for course in sorted(route_courses):
        catalog_course = ENGINE.catalog.get(course)
        if not catalog_course:
            continue
        prereqs = rule_courses(catalog_course.prereq_rule)
        for pre in sorted(prereqs):
            if pre in route_courses:
                lines.append(f"\"{pre}\" -> \"{course}\";")
            elif pre in completed_courses:
                lines.append(f'"{pre}" [label="{pre}\\n(completed)", fillcolor="#dff3e5", color="#4a8b5f"];')
                lines.append(f"\"{pre}\" -> \"{course}\" [style=dashed];")

    lines.append("}")
    return "\n".join(lines)


def list_courses():
    courses = []
    for c in sorted(ENGINE.catalog.values(), key=lambda x: x.code):
        courses.append({"code": c.code, "title": c.title or c.code, "prereq": c.prereq_text})
    terms = sorted(set(ENGINE.term_columns), key=term_sort_key)
    return {
        "courses": courses,
        "graduation_terms": terms,
        "start_term_default": "Spring 2026",
    }


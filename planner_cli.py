import argparse
import json
from pathlib import Path

from planner_engine import PlannerEngine
from azure_llm_client import AzureLLMClient, load_azure_llm_config
from track_recommender import (
    build_track_payload,
    derive_tracks_from_engine,
    recommendation_to_dict,
    recommend_tracks,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic prerequisite + graduation feasibility planner")
    parser.add_argument("--completed", nargs="+", required=True, help="Completed courses, e.g. COMP_SCI 150 COMP_SCI 211")
    parser.add_argument("--targets", nargs="+", required=True, help="Target courses to include")
    parser.add_argument("--start-term", required=True, help="Planning start term, e.g. Spring 2026")
    parser.add_argument("--graduation-term", required=True, help="Target graduation term, e.g. Spring 2027")
    parser.add_argument("--courses-csv", default="main_course_info_typed.csv", help="Path to course catalog CSV")
    parser.add_argument("--degree-md", default="BS_Mccormick_CS.md", help="Path to degree requirement markdown")
    parser.add_argument(
        "--recommend-tracks",
        action="store_true",
        help="Also return track recommendations via Azure LLM (or deterministic fallback).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = Path(__file__).resolve().parent
    courses_csv = str((base / args.courses_csv).resolve())
    degree_md = str((base / args.degree_md).resolve())

    engine = PlannerEngine(courses_csv_path=courses_csv, degree_md_path=degree_md)
    result = engine.plan(
        completed_courses=args.completed,
        target_courses=args.targets,
        start_term=args.start_term,
        graduation_term=args.graduation_term,
    )

    payload = {
        "feasible": result.feasible,
        "message": result.message,
        "routes": result.routes,
        "blockers": result.blockers,
        "alternatives": result.alternatives,
        "degree_audit": {
            "graduation_eligible": result.degree_audit.graduation_eligible,
            "missing_core": result.degree_audit.missing_core,
            "missing_alternative_groups": result.degree_audit.missing_alternative_groups,
            "breadth_remaining": result.degree_audit.breadth_remaining,
            "project_remaining": result.degree_audit.project_remaining,
            "technical_remaining": result.degree_audit.technical_remaining,
            "advanced_remaining": result.degree_audit.advanced_remaining,
        },
    }

    if args.recommend_tracks and result.feasible and result.routes:
        track_to_courses, _ = derive_tracks_from_engine(engine)
        llm_payload = build_track_payload(
            completed_courses=args.completed,
            desired_courses=args.targets,
            graduation_term=args.graduation_term,
            routes=result.routes,
            track_to_courses=track_to_courses,
        )
        llm_client = AzureLLMClient(load_azure_llm_config())
        track_rec = recommend_tracks(llm_client, llm_payload)
        payload["track_recommendation"] = recommendation_to_dict(track_rec)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

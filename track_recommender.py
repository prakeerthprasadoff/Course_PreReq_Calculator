from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional, Set, Tuple

from llm_schemas import (
    FinalTrackPlan,
    TrackOption,
    TrackRecommendation,
    parse_final_track_plan,
    parse_track_recommendation,
)


TRACK_LABELS = {
    "ai": "AI",
    "artificial intelligence": "AI",
    "theory": "Theory",
    "systems": "Systems",
    "interfaces": "Interfaces",
    "software development and programming language": "SoftwareDev",
    "software development": "SoftwareDev",
    "programming language": "SoftwareDev",
    "project course": "Project",
}


def normalize_track_label(raw: str) -> Optional[str]:
    text = raw.strip().lower()
    for key, value in TRACK_LABELS.items():
        if key in text:
            return value
    return None


def derive_tracks_from_engine(engine: Any) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    track_to_courses: Dict[str, Set[str]] = {}
    course_to_tracks: Dict[str, Set[str]] = {}

    for code, course in engine.catalog.items():
        labels = set()
        for course_type in course.course_types:
            parts = [p.strip() for p in course_type.split(",")]
            labels.update(parts)
        for label in labels:
            normalized = normalize_track_label(label)
            if not normalized:
                continue
            track_to_courses.setdefault(normalized, set()).add(code)
            course_to_tracks.setdefault(code, set()).add(normalized)
    return track_to_courses, course_to_tracks


def routes_union_courses(routes: List[Dict[str, List[str]]]) -> Set[str]:
    out: Set[str] = set()
    for route in routes:
        for _, courses in route.items():
            out.update(courses)
    return out


def build_track_payload(
    completed_courses: List[str],
    desired_courses: List[str],
    graduation_term: str,
    routes: List[Dict[str, List[str]]],
    track_to_courses: Dict[str, Set[str]],
) -> Dict[str, Any]:
    feasible_courses = routes_union_courses(routes)
    tracks: List[Dict[str, Any]] = []
    completed_set = set(completed_courses)
    desired_set = set(desired_courses)

    for track, courses in sorted(track_to_courses.items()):
        feasible_in_track = sorted(feasible_courses & courses)
        if not feasible_in_track:
            continue
        tracks.append(
            {
                "track": track,
                "feasible_courses": feasible_in_track,
                "completed_in_track": sorted(completed_set & courses),
                "desired_in_track": sorted(desired_set & courses),
            }
        )

    return {
        "user_profile": {
            "completed_courses": sorted(completed_courses),
            "desired_courses": sorted(desired_courses),
            "graduation_term": graduation_term,
        },
        "feasible_routes": routes,
        "tracks": tracks,
        "guardrails": {
            "only_use_feasible_courses": sorted(feasible_courses),
            "do_not_invent_courses": True,
        },
    }


def deterministic_track_recommendation(payload: Dict[str, Any]) -> TrackRecommendation:
    track_options: List[TrackOption] = []
    for track in payload.get("tracks", []):
        feasible_count = len(track.get("feasible_courses", []))
        completed_count = len(track.get("completed_in_track", []))
        desired_count = len(track.get("desired_in_track", []))
        score = (2 * feasible_count) + (2 * desired_count) + completed_count
        conf = min(0.99, 0.35 + (0.05 * feasible_count))
        rationale = (
            f"{track['track']} has {feasible_count} feasible course(s), "
            f"{completed_count} already completed, and {desired_count} desired overlap."
        )
        aligned_route_index = 1
        track_options.append(
            TrackOption(
                track=track["track"],
                rationale=rationale,
                aligned_route_index=aligned_route_index,
                confidence=round(conf, 2),
            )
        )
        track["_score"] = score

    track_options.sort(key=lambda x: (x.confidence, x.track), reverse=True)
    top = track_options[:4]
    recommended = top[0].track if top else ""
    return TrackRecommendation(
        track_options=top,
        recommended_track=recommended,
        notes="Deterministic fallback recommendation.",
    )


def recommend_tracks(
    llm_client: Any,
    payload: Dict[str, Any],
) -> TrackRecommendation:
    system_prompt = (
        "You are a CS track advisor. Choose only from provided tracks and feasible routes. "
        "Return strict JSON with keys: track_options, recommended_track, notes."
    )
    if not llm_client or not llm_client.available:
        return deterministic_track_recommendation(payload)

    try:
        raw = llm_client.chat_json(system_prompt=system_prompt, user_payload=payload, max_tokens=1200)
        return parse_track_recommendation(raw)
    except Exception:
        return deterministic_track_recommendation(payload)


def validate_final_plan_courses(courses_referenced: List[str], feasible_routes: List[Dict[str, List[str]]]) -> bool:
    feasible = routes_union_courses(feasible_routes)
    return all(course in feasible for course in courses_referenced)


def deterministic_final_plan(track: str, routes: List[Dict[str, List[str]]], route_index: int = 1) -> FinalTrackPlan:
    idx = max(1, route_index)
    if not routes:
        return FinalTrackPlan(
            final_plan_markdown="No feasible route is available for final plan construction.",
            chosen_route_index=1,
            courses_referenced=[],
            notes="Deterministic fallback with no route.",
        )
    chosen = routes[min(idx, len(routes)) - 1]
    lines = [f"Selected Track: **{track}**", ""]
    course_refs: List[str] = []
    for term, courses in chosen.items():
        if not courses:
            continue
        course_refs.extend(courses)
        lines.append(f"- **{term}**: {', '.join(courses)}")
    return FinalTrackPlan(
        final_plan_markdown="\n".join(lines),
        chosen_route_index=min(idx, len(routes)),
        courses_referenced=sorted(set(course_refs)),
        notes="Deterministic fallback final plan.",
    )


def generate_final_track_plan(
    llm_client: Any,
    selected_track: str,
    feasible_routes: List[Dict[str, List[str]]],
    route_hint: int = 1,
) -> FinalTrackPlan:
    payload = {
        "selected_track": selected_track,
        "feasible_routes": feasible_routes,
        "route_hint": route_hint,
        "guardrails": {
            "only_use_courses_from_feasible_routes": sorted(routes_union_courses(feasible_routes)),
            "do_not_invent_courses": True,
        },
    }
    system_prompt = (
        "You are a CS planning assistant. Produce a final plan for the selected track using only feasible routes. "
        "Return strict JSON with keys: final_plan_markdown, chosen_route_index, courses_referenced, notes."
    )
    if not llm_client or not llm_client.available:
        return deterministic_final_plan(selected_track, feasible_routes, route_hint)

    try:
        raw = llm_client.chat_json(system_prompt=system_prompt, user_payload=payload, max_tokens=1400)
        parsed = parse_final_track_plan(raw)
        if not validate_final_plan_courses(parsed.courses_referenced, feasible_routes):
            return deterministic_final_plan(selected_track, feasible_routes, parsed.chosen_route_index)
        return parsed
    except Exception:
        return deterministic_final_plan(selected_track, feasible_routes, route_hint)


def recommendation_to_dict(rec: TrackRecommendation) -> Dict[str, Any]:
    return {
        "track_options": [asdict(x) for x in rec.track_options],
        "recommended_track": rec.recommended_track,
        "notes": rec.notes,
    }

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class TrackOption:
    track: str
    rationale: str
    aligned_route_index: int
    confidence: float


@dataclass
class TrackRecommendation:
    track_options: List[TrackOption]
    recommended_track: str
    notes: str


@dataclass
class FinalTrackPlan:
    final_plan_markdown: str
    chosen_route_index: int
    courses_referenced: List[str]
    notes: str


def _require_keys(payload: Dict[str, Any], keys: List[str]) -> Tuple[bool, str]:
    for key in keys:
        if key not in payload:
            return False, f"Missing required key: {key}"
    return True, ""


def parse_track_recommendation(payload: Dict[str, Any]) -> TrackRecommendation:
    ok, reason = _require_keys(payload, ["track_options", "recommended_track", "notes"])
    if not ok:
        raise ValueError(reason)

    raw_options = payload["track_options"]
    if not isinstance(raw_options, list) or not raw_options:
        raise ValueError("track_options must be a non-empty list")

    parsed: List[TrackOption] = []
    for idx, item in enumerate(raw_options):
        if not isinstance(item, dict):
            raise ValueError(f"track_options[{idx}] must be an object")
        ok, reason = _require_keys(item, ["track", "rationale", "aligned_route_index", "confidence"])
        if not ok:
            raise ValueError(reason)
        parsed.append(
            TrackOption(
                track=str(item["track"]).strip(),
                rationale=str(item["rationale"]).strip(),
                aligned_route_index=int(item["aligned_route_index"]),
                confidence=float(item["confidence"]),
            )
        )

    return TrackRecommendation(
        track_options=parsed,
        recommended_track=str(payload["recommended_track"]).strip(),
        notes=str(payload["notes"]).strip(),
    )


def parse_final_track_plan(payload: Dict[str, Any]) -> FinalTrackPlan:
    ok, reason = _require_keys(payload, ["final_plan_markdown", "chosen_route_index", "courses_referenced", "notes"])
    if not ok:
        raise ValueError(reason)

    courses = payload["courses_referenced"]
    if not isinstance(courses, list):
        raise ValueError("courses_referenced must be a list")

    return FinalTrackPlan(
        final_plan_markdown=str(payload["final_plan_markdown"]).strip(),
        chosen_route_index=int(payload["chosen_route_index"]),
        courses_referenced=[str(c).strip() for c in courses if str(c).strip()],
        notes=str(payload["notes"]).strip(),
    )

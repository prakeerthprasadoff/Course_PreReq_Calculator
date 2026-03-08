from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PlanGenerateRequest(BaseModel):
    completed_courses: List[str]
    desired_courses: List[str]
    start_term: str = "Spring 2026"
    graduation_term: str


class DegreeAuditResponse(BaseModel):
    graduation_eligible: bool
    missing_core: List[str]
    missing_alternative_groups: List[List[str]]
    breadth_remaining: int
    project_remaining: int
    technical_remaining: int
    advanced_remaining: int


class PlanGenerateResponse(BaseModel):
    feasible: bool
    message: str
    routes: List[Dict[str, List[str]]]
    blockers: List[str]
    alternatives: Dict[str, str]
    degree_audit: DegreeAuditResponse


class TrackRecommendRequest(BaseModel):
    completed_courses: List[str]
    desired_courses: List[str]
    graduation_term: str
    routes: List[Dict[str, List[str]]]


class TrackOptionResponse(BaseModel):
    track: str
    rationale: str
    aligned_route_index: int
    confidence: float


class TrackRecommendResponse(BaseModel):
    track_options: List[TrackOptionResponse]
    recommended_track: str
    notes: str
    azure_available: bool
    deterministic_fallback_used: bool


class TrackFinalizeRequest(BaseModel):
    selected_track: str
    routes: List[Dict[str, List[str]]]
    route_hint: int = 1


class TrackFinalizeResponse(BaseModel):
    final_plan_markdown: str
    chosen_route_index: int
    courses_referenced: List[str]
    notes: str
    azure_available: bool
    deterministic_fallback_used: bool


class GraphRouteRequest(BaseModel):
    route: Dict[str, List[str]]
    completed_courses: List[str]
    desired_courses: List[str]


class GraphRouteResponse(BaseModel):
    dot: str


class CourseItem(BaseModel):
    code: str
    title: str
    prereq: str


class CoursesResponse(BaseModel):
    courses: List[CourseItem]
    graduation_terms: List[str]
    start_term_default: str


class HealthResponse(BaseModel):
    ok: bool
    azure_available: bool
    details: Dict[str, Any] = Field(default_factory=dict)

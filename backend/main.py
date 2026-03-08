from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import (
    CoursesResponse,
    GraphRouteRequest,
    GraphRouteResponse,
    HealthResponse,
    PlanGenerateRequest,
    PlanGenerateResponse,
    TrackFinalizeRequest,
    TrackFinalizeResponse,
    TrackRecommendRequest,
    TrackRecommendResponse,
)
from backend.service_adapter import (
    LLM_CLIENT,
    build_route_graph_dot,
    finalize_track_plan,
    generate_plan,
    list_courses,
    plan_to_dict,
    recommend_tracks_for_routes,
)


app = FastAPI(title="Course Planner API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        azure_available=LLM_CLIENT.available,
        details={"mode": "azure" if LLM_CLIENT.available else "deterministic_fallback"},
    )


@app.get("/courses", response_model=CoursesResponse)
def courses() -> CoursesResponse:
    return CoursesResponse(**list_courses())


@app.post("/plan/generate", response_model=PlanGenerateResponse)
def plan_generate(req: PlanGenerateRequest) -> PlanGenerateResponse:
    result = generate_plan(
        completed_courses=req.completed_courses,
        desired_courses=req.desired_courses,
        start_term=req.start_term,
        graduation_term=req.graduation_term,
    )
    return PlanGenerateResponse(**plan_to_dict(result))


@app.post("/tracks/recommend", response_model=TrackRecommendResponse)
def tracks_recommend(req: TrackRecommendRequest) -> TrackRecommendResponse:
    rec = recommend_tracks_for_routes(
        completed_courses=req.completed_courses,
        desired_courses=req.desired_courses,
        graduation_term=req.graduation_term,
        routes=req.routes,
    )
    return TrackRecommendResponse(**rec)


@app.post("/tracks/finalize", response_model=TrackFinalizeResponse)
def tracks_finalize(req: TrackFinalizeRequest) -> TrackFinalizeResponse:
    final = finalize_track_plan(
        selected_track=req.selected_track,
        routes=req.routes,
        route_hint=req.route_hint,
    )
    return TrackFinalizeResponse(**final)


@app.post("/graph/route", response_model=GraphRouteResponse)
def graph_route(req: GraphRouteRequest) -> GraphRouteResponse:
    dot = build_route_graph_dot(
        route=req.route,
        completed_courses=set(req.completed_courses),
        desired_courses=set(req.desired_courses),
    )
    return GraphRouteResponse(dot=dot)


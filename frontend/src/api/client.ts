import axios from "axios";
import type {
  CoursesResponse,
  HealthResponse,
  PlanResponse,
  RouteMap,
  TrackFinalizeResponse,
  TrackRecommendResponse,
} from "./types";

const baseURL = import.meta.env.VITE_API_BASE_URL || "";

const api = axios.create({
  baseURL,
  timeout: 30000,
});

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health");
  return data;
}

export async function getCourses(): Promise<CoursesResponse> {
  const { data } = await api.get<CoursesResponse>("/courses");
  return data;
}

export async function generatePlan(payload: {
  completed_courses: string[];
  desired_courses: string[];
  start_term: string;
  graduation_term: string;
}): Promise<PlanResponse> {
  const { data } = await api.post<PlanResponse>("/plan/generate", payload);
  return data;
}

export async function recommendTracks(payload: {
  completed_courses: string[];
  desired_courses: string[];
  graduation_term: string;
  routes: RouteMap[];
}): Promise<TrackRecommendResponse> {
  const { data } = await api.post<TrackRecommendResponse>("/tracks/recommend", payload);
  return data;
}

export async function finalizeTrack(payload: {
  selected_track: string;
  routes: RouteMap[];
  route_hint: number;
}): Promise<TrackFinalizeResponse> {
  const { data } = await api.post<TrackFinalizeResponse>("/tracks/finalize", payload);
  return data;
}

export async function getRouteGraphDot(payload: {
  route: RouteMap;
  completed_courses: string[];
  desired_courses: string[];
}): Promise<{ dot: string }> {
  const { data } = await api.post<{ dot: string }>("/graph/route", payload);
  return data;
}

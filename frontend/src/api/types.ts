export type RouteMap = Record<string, string[]>;

export interface DegreeAudit {
  graduation_eligible: boolean;
  missing_core: string[];
  missing_alternative_groups: string[][];
  breadth_remaining: number;
  project_remaining: number;
  technical_remaining: number;
  advanced_remaining: number;
}

export interface PlanResponse {
  feasible: boolean;
  message: string;
  routes: RouteMap[];
  blockers: string[];
  alternatives: Record<string, string>;
  degree_audit: DegreeAudit;
}

export interface TrackOption {
  track: string;
  rationale: string;
  aligned_route_index: number;
  confidence: number;
}

export interface TrackRecommendResponse {
  track_options: TrackOption[];
  recommended_track: string;
  notes: string;
  azure_available: boolean;
  deterministic_fallback_used: boolean;
}

export interface TrackFinalizeResponse {
  final_plan_markdown: string;
  chosen_route_index: number;
  courses_referenced: string[];
  notes: string;
  azure_available: boolean;
  deterministic_fallback_used: boolean;
}

export interface CourseItem {
  code: string;
  title: string;
  prereq: string;
}

export interface CoursesResponse {
  courses: CourseItem[];
  graduation_terms: string[];
  start_term_default: string;
}

export interface HealthResponse {
  ok: boolean;
  azure_available: boolean;
  details: Record<string, unknown>;
}

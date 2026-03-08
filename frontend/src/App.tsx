import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import "./App.css";
import {
  finalizeTrack,
  generatePlan,
  getCourses,
  getHealth,
  getRouteGraphDot,
  recommendTracks,
} from "./api/client";
import type { PlanResponse, RouteMap, TrackFinalizeResponse, TrackRecommendResponse } from "./api/types";
import RouteGraphModal from "./components/RouteGraphModal";

function parseCourseInput(text: string): string[] {
  return text
    .split(/[,\n]/g)
    .map((x) => x.trim())
    .filter(Boolean);
}

function markdownToListLines(markdown: string): string[] {
  return markdown
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function App() {
  const [completedText, setCompletedText] = useState("");
  const [desiredText, setDesiredText] = useState("");
  const [selectedCompleted, setSelectedCompleted] = useState<string[]>([]);
  const [selectedDesired, setSelectedDesired] = useState<string[]>([]);
  const [graduationTerm, setGraduationTerm] = useState("Spring 2027");
  const [startTerm, setStartTerm] = useState("Spring 2026");
  const [routeIndex, setRouteIndex] = useState(1);
  const [selectedTrack, setSelectedTrack] = useState<string>("");
  const [graphOpen, setGraphOpen] = useState(false);
  const [graphDot, setGraphDot] = useState("");

  const [planResult, setPlanResult] = useState<PlanResponse | null>(null);
  const [trackResult, setTrackResult] = useState<TrackRecommendResponse | null>(null);
  const [finalTrackPlan, setFinalTrackPlan] = useState<TrackFinalizeResponse | null>(null);

  const coursesQuery = useQuery({
    queryKey: ["courses"],
    queryFn: getCourses,
  });
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    retry: false,
  });

  const allCourseCodes = useMemo(
    () => coursesQuery.data?.courses.map((c) => c.code) ?? [],
    [coursesQuery.data]
  );
  const graduationTerms = coursesQuery.data?.graduation_terms ?? [graduationTerm];

  const effectiveCompleted = useMemo(() => {
    const fromText = parseCourseInput(completedText);
    return Array.from(new Set([...selectedCompleted, ...fromText]));
  }, [completedText, selectedCompleted]);

  const effectiveDesired = useMemo(() => {
    const fromText = parseCourseInput(desiredText);
    return Array.from(new Set([...selectedDesired, ...fromText]));
  }, [desiredText, selectedDesired]);

  const planMutation = useMutation({
    mutationFn: generatePlan,
    onSuccess: async (data) => {
      setPlanResult(data);
      setTrackResult(null);
      setFinalTrackPlan(null);
      setSelectedTrack("");

      if (!data.feasible || !data.routes.length) return;
      const rec = await recommendTracks({
        completed_courses: effectiveCompleted,
        desired_courses: effectiveDesired,
        graduation_term: graduationTerm,
        routes: data.routes,
      });
      setTrackResult(rec);
    },
  });

  const finalizeMutation = useMutation({
    mutationFn: finalizeTrack,
    onSuccess: (data) => setFinalTrackPlan(data),
  });

  const openGraphForRoute = async (route: RouteMap) => {
    const { dot } = await getRouteGraphDot({
      route,
      completed_courses: effectiveCompleted,
      desired_courses: effectiveDesired,
    });
    setGraphDot(dot);
    setGraphOpen(true);
  };

  return (
    <div className="page">
      <h1>Course Pre-Req Planner</h1>
      <p className="muted">
        React UI with existing Python planner + Azure LLM recommendations.
      </p>

      <div className="card-grid">
        <section className="card">
          <h2>Completed Courses</h2>
          <textarea
            value={completedText}
            onChange={(e) => setCompletedText(e.target.value)}
            placeholder="COMP_SCI 150, COMP_SCI 211"
          />
          <label>Quick select completed</label>
          <select
            multiple
            value={selectedCompleted}
            onChange={(e) =>
              setSelectedCompleted(Array.from(e.target.selectedOptions).map((x) => x.value))
            }
          >
            {allCourseCodes.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </section>

        <section className="card">
          <h2>Desired Courses</h2>
          <textarea
            value={desiredText}
            onChange={(e) => setDesiredText(e.target.value)}
            placeholder="COMP_SCI 308"
          />
          <label>Quick select desired</label>
          <select
            multiple
            value={selectedDesired}
            onChange={(e) =>
              setSelectedDesired(Array.from(e.target.selectedOptions).map((x) => x.value))
            }
          >
            {allCourseCodes.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </section>
      </div>

      <section className="card">
        <h2>Plan Settings</h2>
        <div className="row">
          <div>
            <label>Start Term</label>
            <input value={startTerm} onChange={(e) => setStartTerm(e.target.value)} />
          </div>
          <div>
            <label>Graduation Term</label>
            <select value={graduationTerm} onChange={(e) => setGraduationTerm(e.target.value)}>
              {graduationTerms.map((term) => (
                <option key={term} value={term}>
                  {term}
                </option>
              ))}
            </select>
          </div>
          <div className="status-box">
            <span>Azure:</span>
            <strong>
              {healthQuery.data?.azure_available ? "connected" : "not configured/fallback"}
            </strong>
          </div>
        </div>
        <button
          className="primary"
          disabled={!effectiveCompleted.length || !effectiveDesired.length || planMutation.isPending}
          onClick={() =>
            planMutation.mutate({
              completed_courses: effectiveCompleted,
              desired_courses: effectiveDesired,
              start_term: startTerm,
              graduation_term: graduationTerm,
            })
          }
        >
          {planMutation.isPending ? "Generating..." : "Generate Plan"}
        </button>
      </section>

      {planResult && (
        <section className="card">
          <h2>Your Course Plan</h2>
          <p>{planResult.message}</p>
          {!planResult.feasible && (
            <>
              <h3>Blockers</h3>
              <ul>
                {planResult.blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </>
          )}

          {planResult.feasible && (
            <>
              <div className="row">
                <div>
                  <label>Route to visualize</label>
                  <select
                    value={routeIndex}
                    onChange={(e) => setRouteIndex(parseInt(e.target.value, 10))}
                  >
                    {planResult.routes.map((_, idx) => (
                      <option key={idx + 1} value={idx + 1}>
                        Route {idx + 1}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={() => openGraphForRoute(planResult.routes[Math.max(0, routeIndex - 1)])}
                >
                  View Course Graph
                </button>
              </div>

              {planResult.routes.map((route, idx) => (
                <details key={idx} open={idx === 0}>
                  <summary>Feasible Route {idx + 1}</summary>
                  <ul>
                    {Object.entries(route).map(([term, courses]) =>
                      courses.length ? <li key={term}><strong>{term}:</strong> {courses.join(", ")}</li> : null
                    )}
                  </ul>
                </details>
              ))}
            </>
          )}
        </section>
      )}

      {trackResult && (
        <section className="card">
          <h2>Suggested Track Plans</h2>
          <p>
            Recommended track: <strong>{trackResult.recommended_track}</strong>
          </p>
          <p className="muted">{trackResult.notes}</p>
          <p className="muted">
            Source: {trackResult.azure_available ? "Azure connected" : "Deterministic"} | Fallback used:{" "}
            {trackResult.deterministic_fallback_used ? "Yes" : "No"}
          </p>
          <div className="button-row">
            {trackResult.track_options.map((opt) => (
              <button
                key={opt.track}
                onClick={() => {
                  setSelectedTrack(opt.track);
                  if (!planResult) return;
                  finalizeMutation.mutate({
                    selected_track: opt.track,
                    routes: planResult.routes,
                    route_hint: opt.aligned_route_index,
                  });
                }}
              >
                {opt.track} ({opt.confidence.toFixed(2)})
              </button>
            ))}
          </div>
        </section>
      )}

      {selectedTrack && finalTrackPlan && (
        <section className="card">
          <h2>Final Plan for {selectedTrack}</h2>
          <ul>
            {markdownToListLines(finalTrackPlan.final_plan_markdown).map((line, i) => (
              <li key={`${line}-${i}`}>{line.replace(/^-\s*/, "")}</li>
            ))}
          </ul>
          <p className="muted">{finalTrackPlan.notes}</p>
          <p className="muted">
            Source: {finalTrackPlan.azure_available ? "Azure connected" : "Deterministic"} | Fallback used:{" "}
            {finalTrackPlan.deterministic_fallback_used ? "Yes" : "No"}
          </p>
        </section>
      )}

      <RouteGraphModal isOpen={graphOpen} onClose={() => setGraphOpen(false)} dot={graphDot} />
    </div>
  );
}

export default App;

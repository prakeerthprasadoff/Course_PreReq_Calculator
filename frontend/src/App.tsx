import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Alert,
  AppBar,
  Autocomplete,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from "@mui/material";
import {
  AutoAwesomeRounded,
  HubRounded,
  InsightsRounded,
  SchoolRounded,
  TimelineRounded,
} from "@mui/icons-material";
import { motion } from "framer-motion";
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

const SEASON_ORDER: Record<string, number> = { Winter: 1, Spring: 2, Summer: 3, Fall: 4 };

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

function parseTerm(term: string): { season: string; year: number } | null {
  const match = /^([A-Za-z]+)\s+(\d{4})$/.exec(term.trim());
  if (!match) return null;
  const season = `${match[1][0].toUpperCase()}${match[1].slice(1).toLowerCase()}`;
  const year = Number(match[2]);
  if (!SEASON_ORDER[season] || Number.isNaN(year)) return null;
  return { season, year };
}

function termSortValue(term: string): number {
  const parsed = parseTerm(term);
  if (!parsed) return Number.MAX_SAFE_INTEGER;
  return parsed.year * 10 + SEASON_ORDER[parsed.season];
}

function nextTerm(term: string): string {
  const parsed = parseTerm(term);
  if (!parsed) return term;
  if (parsed.season === "Winter") return `Spring ${parsed.year}`;
  if (parsed.season === "Spring") return `Summer ${parsed.year}`;
  if (parsed.season === "Summer") return `Fall ${parsed.year}`;
  return `Winter ${parsed.year + 1}`;
}

function buildTermOptions(baseTerms: string[], startTerm: string, graduationTerm: string): string[] {
  const terms = new Set<string>([...baseTerms, startTerm, graduationTerm]);
  let sorted = Array.from(terms).sort((a, b) => termSortValue(a) - termSortValue(b));
  const valid = sorted.filter((t) => parseTerm(t));
  if (!valid.length) return sorted;

  let cursor = valid[valid.length - 1];
  for (let i = 0; i < 8; i += 1) {
    cursor = nextTerm(cursor);
    terms.add(cursor);
  }
  return Array.from(terms).sort((a, b) => termSortValue(a) - termSortValue(b));
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

  const courseItems = coursesQuery.data?.courses ?? [];
  const courseLookup = useMemo(
    () => new Map(courseItems.map((course) => [course.code, `${course.code} - ${course.title || course.code}`])),
    [courseItems]
  );
  const courseCodeSet = useMemo(() => new Set(courseItems.map((course) => course.code)), [courseItems]);
  const graduationTerms = useMemo(
    () => buildTermOptions(coursesQuery.data?.graduation_terms ?? [], startTerm, graduationTerm),
    [coursesQuery.data, graduationTerm, startTerm]
  );

  useEffect(() => {
    const apiStart = coursesQuery.data?.start_term_default;
    if (!apiStart) return;
    setStartTerm((prev) => prev || apiStart);
  }, [coursesQuery.data]);

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
      setRouteIndex(1);
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

  const routeCount = planResult?.routes.length ?? 0;
  const selectedRoute =
    planResult?.routes[Math.max(0, Math.min(routeIndex - 1, Math.max(0, routeCount - 1)))] ?? null;
  const statusLabel = healthQuery.data?.azure_available ? "Azure Connected" : "Deterministic Mode";
  const statusColor: "success" | "warning" = healthQuery.data?.azure_available ? "success" : "warning";

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at 10% 20%, rgba(14, 165, 233, 0.10), transparent 30%), radial-gradient(circle at 90% 10%, rgba(79, 70, 229, 0.12), transparent 34%), linear-gradient(180deg, #f8fbff 0%, #eef2ff 100%)",
      }}
    >
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          background: "linear-gradient(92deg, #1d4ed8 0%, #4f46e5 52%, #7c3aed 100%)",
          borderBottom: "1px solid rgba(255,255,255,0.18)",
          backdropFilter: "blur(8px)",
        }}
      >
        <Toolbar>
          <Stack direction="row" alignItems="center" spacing={1.5} sx={{ flexGrow: 1 }}>
            <Avatar sx={{ bgcolor: "rgba(255,255,255,0.22)", width: 36, height: 36 }}>
              <SchoolRounded fontSize="small" />
            </Avatar>
            <Box>
              <Typography variant="h6" fontWeight={800} sx={{ lineHeight: 1.2 }}>
                Course Pre-Req Planner
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.88 }}>
                Build your roadmap, then optimize your specialization track
              </Typography>
            </Box>
          </Stack>
          <Chip label={statusLabel} color={statusColor} variant="filled" />
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {[
            { icon: <TimelineRounded fontSize="small" />, label: "Active Routes", value: routeCount || "-" },
            { icon: <HubRounded fontSize="small" />, label: "Catalog Courses", value: courseItems.length || "-" },
            {
              icon: <InsightsRounded fontSize="small" />,
              label: "Track Engine",
              value: trackResult?.recommended_track || "Awaiting plan",
            },
          ].map((item, idx) => (
            <Grid key={item.label} size={{ xs: 12, md: 4 }}>
              <Box
                component={motion.div}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08 * idx, duration: 0.35 }}
              >
                <Card
                  sx={{
                    background: "linear-gradient(120deg, rgba(255,255,255,0.94), rgba(255,255,255,0.82))",
                    backdropFilter: "blur(10px)",
                  }}
                >
                  <CardContent sx={{ py: 2.1 }}>
                    <Stack direction="row" spacing={1.2} alignItems="center">
                      <Avatar
                        sx={{
                          bgcolor: "rgba(79, 70, 229, 0.12)",
                          color: "primary.main",
                          width: 34,
                          height: 34,
                        }}
                      >
                        {item.icon}
                      </Avatar>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          {item.label}
                        </Typography>
                        <Typography variant="subtitle1" fontWeight={700}>
                          {item.value}
                        </Typography>
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>
              </Box>
            </Grid>
          ))}
        </Grid>

        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Box
              component={motion.div}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              <Paper
                elevation={1}
                sx={{ p: 3, borderRadius: 4, background: "linear-gradient(160deg, #ffffff 0%, #f8fbff 100%)" }}
              >
                <Typography variant="h6" fontWeight={700} gutterBottom>
                  Completed Courses
                </Typography>
                <Autocomplete
                  multiple
                  options={courseItems.map((course) => course.code)}
                  value={selectedCompleted}
                  onChange={(_, value) => setSelectedCompleted(value)}
                  renderInput={(params) => (
                    <TextField {...params} label="Quick select completed courses" placeholder="Choose courses" />
                  )}
                  renderOption={(props, option) => (
                    <li {...props} key={option}>
                      {courseLookup.get(option) ?? option}
                    </li>
                  )}
                  sx={{ mb: 2 }}
                />
                <TextField
                  fullWidth
                  multiline
                  minRows={4}
                  value={completedText}
                  onChange={(e) => setCompletedText(e.target.value)}
                  label="Or paste completed courses"
                  placeholder="COMP_SCI 150, COMP_SCI 211"
                  helperText="Comma or new-line separated"
                />
                <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} useFlexGap flexWrap="wrap">
                  {effectiveCompleted.slice(0, 5).map((code) => (
                    <Chip key={`done-${code}`} size="small" label={courseLookup.get(code) ?? code} />
                  ))}
                  {effectiveCompleted.length > 5 && (
                    <Chip size="small" color="primary" label={`+${effectiveCompleted.length - 5} more`} />
                  )}
                </Stack>
              </Paper>
            </Box>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <Box
              component={motion.div}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.07 }}
            >
              <Paper
                elevation={1}
                sx={{ p: 3, borderRadius: 4, background: "linear-gradient(160deg, #ffffff 0%, #f8fbff 100%)" }}
              >
                <Typography variant="h6" fontWeight={700} gutterBottom>
                  Desired Courses
                </Typography>
                <Autocomplete
                  multiple
                  options={courseItems.map((course) => course.code)}
                  value={selectedDesired}
                  onChange={(_, value) => setSelectedDesired(value)}
                  renderInput={(params) => (
                    <TextField {...params} label="Quick select desired courses" placeholder="Choose courses" />
                  )}
                  renderOption={(props, option) => (
                    <li {...props} key={option}>
                      {courseLookup.get(option) ?? option}
                    </li>
                  )}
                  sx={{ mb: 2 }}
                />
                <TextField
                  fullWidth
                  multiline
                  minRows={4}
                  value={desiredText}
                  onChange={(e) => setDesiredText(e.target.value)}
                  label="Or paste desired courses"
                  placeholder="COMP_SCI 349"
                  helperText="Comma or new-line separated"
                />
                <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} useFlexGap flexWrap="wrap">
                  {effectiveDesired.slice(0, 5).map((code) => (
                    <Chip
                      key={`want-${code}`}
                      size="small"
                      color="secondary"
                      variant="outlined"
                      label={courseLookup.get(code) ?? code}
                    />
                  ))}
                  {effectiveDesired.length > 5 && (
                    <Chip size="small" color="secondary" label={`+${effectiveDesired.length - 5} more`} />
                  )}
                </Stack>
              </Paper>
            </Box>
          </Grid>

          <Grid size={12}>
            <Paper
              elevation={1}
              sx={{
                p: 3,
                borderRadius: 4,
                background:
                  "linear-gradient(120deg, rgba(79,70,229,0.06), rgba(6,182,212,0.06) 60%, rgba(124,58,237,0.08))",
              }}
            >
              <Typography variant="h6" fontWeight={700} gutterBottom>
                Planning Settings
              </Typography>
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 12, md: 4 }}>
                  <FormControl fullWidth>
                    <InputLabel>Start Term</InputLabel>
                    <Select value={startTerm} label="Start Term" onChange={(e) => setStartTerm(e.target.value)}>
                      {graduationTerms.map((term) => (
                        <MenuItem key={`start-${term}`} value={term}>
                          {term}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <FormControl fullWidth>
                    <InputLabel>Graduation Term</InputLabel>
                    <Select
                      value={graduationTerm}
                      label="Graduation Term"
                      onChange={(e) => setGraduationTerm(e.target.value)}
                    >
                      {graduationTerms.map((term) => (
                        <MenuItem key={`grad-${term}`} value={term}>
                          {term}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Button
                    variant="contained"
                    size="large"
                    fullWidth
                    disabled={!effectiveCompleted.length || !effectiveDesired.length || planMutation.isPending}
                    onClick={() =>
                      planMutation.mutate({
                        completed_courses: effectiveCompleted,
                        desired_courses: effectiveDesired,
                        start_term: startTerm,
                        graduation_term: graduationTerm,
                      })
                    }
                    sx={{ py: 1.5, fontWeight: 700, borderRadius: 2 }}
                  >
                    {planMutation.isPending ? (
                      <Stack direction="row" spacing={1} alignItems="center">
                        <CircularProgress color="inherit" size={18} />
                        <span>Generating Plan...</span>
                      </Stack>
                    ) : (
                      "Generate Plan"
                    )}
                  </Button>
                </Grid>
              </Grid>
              {!!effectiveDesired.some((code) => !courseCodeSet.has(code)) && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Some desired courses were manually entered and are not in the catalog list; planner will still try
                  normalization.
                </Alert>
              )}
            </Paper>
          </Grid>
        </Grid>

        {planResult && (
          <Box component={motion.div} initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}>
            <Paper elevation={1} sx={{ p: 3, borderRadius: 4, mt: 3 }}>
              <Typography variant="h6" fontWeight={700} gutterBottom>
                Planner Output
              </Typography>
              <Alert severity={planResult.feasible ? "success" : "warning"} sx={{ mb: 2 }}>
                {planResult.message}
              </Alert>

              {!planResult.feasible && planResult.blockers.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    Blockers
                  </Typography>
                  <ul>
                    {planResult.blockers.map((blocker) => (
                      <li key={blocker}>{blocker}</li>
                    ))}
                  </ul>
                </Box>
              )}

              {!planResult.feasible && Object.keys(planResult.alternatives || {}).length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    Alternative options
                  </Typography>
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
                    {Object.entries(planResult.alternatives).map(([key, value]) => (
                      <Chip
                        key={`${key}-${value}`}
                        color="secondary"
                        variant="outlined"
                        label={`${key.replaceAll("_", " ")}: ${value}`}
                      />
                    ))}
                  </Stack>
                </Box>
              )}

              {planResult.feasible && (
                <>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 2 }}>
                    <FormControl sx={{ minWidth: 220 }}>
                      <InputLabel>Route</InputLabel>
                      <Select
                        value={String(routeIndex)}
                        label="Route"
                        onChange={(e) => setRouteIndex(Number(e.target.value))}
                      >
                        {planResult.routes.map((_, idx) => (
                          <MenuItem key={idx + 1} value={String(idx + 1)}>
                            Route {idx + 1}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <Button
                      variant="outlined"
                      startIcon={<TimelineRounded />}
                      onClick={() => selectedRoute && openGraphForRoute(selectedRoute)}
                    >
                      View Course Graph
                    </Button>
                  </Stack>

                  {selectedRoute && (
                    <Paper
                      key={`route-${routeIndex}`}
                      variant="outlined"
                      sx={{
                        mb: 2,
                        p: 2,
                        borderRadius: 3,
                        background: "linear-gradient(120deg, rgba(79,70,229,0.08), rgba(6,182,212,0.06))",
                      }}
                    >
                      <Typography variant="subtitle1" fontWeight={700} gutterBottom>
                        Feasible Route {routeIndex}
                      </Typography>
                      <Stack spacing={1.2}>
                        {Object.entries(selectedRoute).map(([term, courses]) =>
                          courses.length ? (
                            <Box key={`${routeIndex}-${term}`} sx={{ pb: 1 }}>
                              <Chip size="small" label={term} sx={{ mb: 1 }} />
                              <Divider sx={{ mb: 1 }} />
                              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                                {courses.map((course) => {
                                  const isDesired = effectiveDesired.includes(course);
                                  return (
                                    <Chip
                                      key={`${routeIndex}-${term}-${course}`}
                                      color={isDesired ? "secondary" : "default"}
                                      variant={isDesired ? "filled" : "outlined"}
                                      label={courseLookup.get(course) ?? course}
                                    />
                                  );
                                })}
                              </Stack>
                            </Box>
                          ) : null
                        )}
                      </Stack>
                    </Paper>
                  )}
                </>
              )}
            </Paper>
          </Box>
        )}

        {trackResult && (
          <Box component={motion.div} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <Paper elevation={1} sx={{ p: 3, borderRadius: 4, mt: 3 }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <AutoAwesomeRounded color="primary" fontSize="small" />
                <Typography variant="h6" fontWeight={700}>
                  Suggested Track Plans
                </Typography>
              </Stack>
              <Typography sx={{ mb: 1 }}>
                Recommended track: <strong>{trackResult.recommended_track}</strong>
              </Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                {trackResult.notes}
              </Typography>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} useFlexGap flexWrap="wrap">
                {trackResult.track_options.map((opt) => (
                  <Button
                    key={opt.track}
                    variant={selectedTrack === opt.track ? "contained" : "outlined"}
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
                  </Button>
                ))}
              </Stack>
            </Paper>
          </Box>
        )}

        {selectedTrack && finalTrackPlan && (
          <Box component={motion.div} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <Paper
              elevation={1}
              sx={{
                p: 3,
                borderRadius: 4,
                mt: 3,
                mb: 3,
                background: "linear-gradient(120deg, rgba(79,70,229,0.06), rgba(6,182,212,0.06))",
              }}
            >
              <Typography variant="h6" fontWeight={700} gutterBottom>
                Final Plan - {selectedTrack}
              </Typography>
              <ul>
                {markdownToListLines(finalTrackPlan.final_plan_markdown).map((line, i) => (
                  <li key={`${line}-${i}`}>{line.replace(/^-\s*/, "")}</li>
                ))}
              </ul>
              <Typography color="text.secondary">{finalTrackPlan.notes}</Typography>
            </Paper>
          </Box>
        )}

        {coursesQuery.isLoading && (
          <Paper sx={{ mt: 3, p: 2.5, textAlign: "center" }}>
            <Stack direction="row" spacing={1} alignItems="center" justifyContent="center">
              <CircularProgress size={18} />
              <Typography>Loading course catalog...</Typography>
            </Stack>
          </Paper>
        )}

        {(coursesQuery.isError || healthQuery.isError) && (
          <Alert severity="error" sx={{ mt: 3 }}>
            Could not reach backend service. Ensure FastAPI is running on `http://127.0.0.1:8000`.
          </Alert>
        )}
      </Container>

      <RouteGraphModal isOpen={graphOpen} onClose={() => setGraphOpen(false)} dot={graphDot} />
    </Box>
  );
}

export default App;

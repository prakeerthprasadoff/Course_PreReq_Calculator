from __future__ import annotations

import csv
import itertools
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import networkx as nx


SEASON_ORDER = {"Winter": 0, "Spring": 1, "Summer": 2, "Fall": 3}
TERM_PATTERN = re.compile(r"^(Fall|Winter|Spring|Summer)\s+(\d{4})$", re.IGNORECASE)


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def normalize_dept(dept: str) -> str:
    d = dept.upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "CS": "COMP_SCI",
        "CE": "COMP_ENG",
        "EE": "ELEC_ENG",
    }
    return aliases.get(d, d)


def normalize_course_code(raw: str, default_dept: Optional[str] = None) -> Optional[str]:
    value = normalize_space(raw).upper().replace("–", "-").replace("—", "-")
    value = value.replace("  ", " ")
    value = value.replace("-", " - ")
    value = normalize_space(value)

    full_match = re.search(r"([A-Z_\/]+)\s*-?\s*(\d{3})(?:\s*-\s*(\d))?", value)
    if full_match:
        dept_part = full_match.group(1)
        number = full_match.group(2)
        suffix = full_match.group(3)
        if "/" in dept_part:
            # Caller can split cross-lists using expand_course_field
            dept_part = dept_part.split("/")[0]
        dept = normalize_dept(dept_part)
        if suffix:
            return f"{dept} {number}-{suffix}"
        return f"{dept} {number}"

    bare_match = re.search(r"\b(\d{3})(?:\s*-\s*(\d))?\b", value)
    if bare_match and default_dept:
        number = bare_match.group(1)
        suffix = bare_match.group(2)
        if suffix:
            return f"{default_dept} {number}-{suffix}"
        return f"{default_dept} {number}"
    return None


def expand_course_field(field_value: str) -> List[str]:
    if not field_value:
        return []
    raw = field_value.strip()
    chunks = [normalize_space(c) for c in raw.split(",") if c.strip()]
    result: List[str] = []
    default_dept: Optional[str] = None

    for chunk in chunks:
        cross_match = re.search(r"([A-Z_]+/[A-Z_]+)\s*(\d{3}(?:-\d)?)", chunk.upper())
        if cross_match:
            depts = cross_match.group(1).split("/")
            num = cross_match.group(2)
            for dept in depts:
                code = normalize_course_code(f"{dept} {num}")
                if code:
                    result.append(code)
                    default_dept = code.split()[0]
            continue

        code = normalize_course_code(chunk, default_dept=default_dept)
        if code:
            result.append(code)
            default_dept = code.split()[0]
    return sorted(set(result))


@dataclass(frozen=True)
class Rule:
    op: str
    children: Tuple["Rule", ...] = ()
    course: Optional[str] = None


TRUE_RULE = Rule(op="TRUE")


def extract_course_codes_with_context(text: str) -> List[str]:
    if not text:
        return []
    cleaned = text.upper().replace("–", "-").replace("—", "-")
    segments = [normalize_space(s) for s in re.split(r"[,;/]+", cleaned)]
    codes: List[str] = []
    default_dept: Optional[str] = None
    for seg in segments:
        if not seg:
            continue
        if "/" in seg and re.search(r"[A-Z_]+/[A-Z_]+\s*\d{3}", seg):
            cross = re.search(r"([A-Z_]+/[A-Z_]+)\s*(\d{3}(?:-\d)?)", seg)
            if cross:
                for dept in cross.group(1).split("/"):
                    code = normalize_course_code(f"{dept} {cross.group(2)}")
                    if code:
                        codes.append(code)
                        default_dept = code.split()[0]
            continue

        explicit = normalize_course_code(seg, default_dept=default_dept)
        if explicit:
            codes.append(explicit)
            default_dept = explicit.split()[0]
            continue

        bare_codes = re.findall(r"\b(\d{3})(?:\s*-\s*(\d))?\b", seg)
        for number, suffix in bare_codes:
            if default_dept:
                if suffix:
                    codes.append(f"{default_dept} {number}-{suffix}")
                else:
                    codes.append(f"{default_dept} {number}")
    return sorted(set(codes))


def parse_prereq_rule(text: str) -> Rule:
    if not text or not text.strip():
        return TRUE_RULE

    lowered = f" {text.lower()} "
    or_parts = [p.strip() for p in re.split(r"\bor\b", lowered) if p.strip()]
    if len(or_parts) > 1:
        options: List[Rule] = []
        for part in or_parts:
            courses = extract_course_codes_with_context(part)
            if not courses:
                continue
            if len(courses) == 1:
                options.append(Rule(op="COURSE", course=courses[0]))
            else:
                options.append(Rule(op="AND", children=tuple(Rule(op="COURSE", course=c) for c in courses)))
        return Rule(op="OR", children=tuple(options)) if options else TRUE_RULE

    courses = extract_course_codes_with_context(text)
    if not courses:
        return TRUE_RULE
    if len(courses) == 1:
        return Rule(op="COURSE", course=courses[0])
    return Rule(op="AND", children=tuple(Rule(op="COURSE", course=c) for c in courses))


def evaluate_rule(rule: Rule, completed: Set[str]) -> bool:
    if rule.op == "TRUE":
        return True
    if rule.op == "COURSE":
        return bool(rule.course in completed)
    if rule.op == "AND":
        return all(evaluate_rule(child, completed) for child in rule.children)
    if rule.op == "OR":
        return any(evaluate_rule(child, completed) for child in rule.children)
    return True


def rule_courses(rule: Rule) -> Set[str]:
    if rule.op == "COURSE" and rule.course:
        return {rule.course}
    out: Set[str] = set()
    for child in rule.children:
        out.update(rule_courses(child))
    return out


def policy_flags_from_text(text: str) -> Set[str]:
    flags: Set[str] = set()
    if not text:
        return flags
    lowered = text.lower()
    if "ic" in lowered or "instructor consent" in lowered:
        flags.add("IC")
    if "graduate" in lowered or "phd" in lowered or "ms cs" in lowered:
        flags.add("GRAD_STANDING")
    if "senior" in lowered:
        flags.add("SENIOR_ONLY")
    if "junior" in lowered:
        flags.add("JUNIOR_ONLY")
    if "major" in lowered:
        flags.add("MAJOR_CONSTRAINT")
    return flags


@dataclass
class Course:
    code: str
    title: str
    offerings: Set[str] = field(default_factory=set)
    offered_seasons: Set[str] = field(default_factory=set)
    prereq_text: str = ""
    prereq_rule: Rule = TRUE_RULE
    policy_flags: Set[str] = field(default_factory=set)
    course_types: Set[str] = field(default_factory=set)


@dataclass
class DegreeRequirements:
    core_required: Set[str]
    core_alternatives: List[Set[str]]
    breadth_courses: Set[str]
    project_courses: Set[str]
    technical_courses: Set[str]
    advanced_intro_support: Set[str]


@dataclass
class DegreeAuditResult:
    graduation_eligible: bool
    missing_core: List[str]
    missing_alternative_groups: List[List[str]]
    breadth_remaining: int
    project_remaining: int
    technical_remaining: int
    advanced_remaining: int


@dataclass
class PlanResult:
    feasible: bool
    message: str
    routes: List[Dict[str, List[str]]]
    blockers: List[str]
    alternatives: Dict[str, str]
    degree_audit: DegreeAuditResult


def parse_term(term_str: str) -> Tuple[str, int]:
    m = TERM_PATTERN.match(normalize_space(term_str))
    if not m:
        raise ValueError(f"Invalid term format: {term_str}. Use e.g. 'Spring 2027'.")
    season = m.group(1).title()
    year = int(m.group(2))
    return season, year


def term_sort_key(term: str) -> Tuple[int, int]:
    season, year = parse_term(term)
    return year, SEASON_ORDER[season]


def next_term(term: str) -> str:
    season, year = parse_term(term)
    if season == "Winter":
        return f"Spring {year}"
    if season == "Spring":
        return f"Summer {year}"
    if season == "Summer":
        return f"Fall {year}"
    return f"Winter {year + 1}"


def generate_terms(start_term: str, end_term: str) -> List[str]:
    terms = []
    cur = start_term
    while term_sort_key(cur) <= term_sort_key(end_term):
        terms.append(cur)
        cur = next_term(cur)
    return terms


def extract_course_code_from_line(line: str) -> Optional[str]:
    return normalize_course_code(line)


def parse_degree_requirements(md_path: str) -> DegreeRequirements:
    with open(md_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines()]

    core_required = {"COMP_SCI 150", "COMP_SCI 211", "COMP_SCI 213", "COMP_SCI 214"}
    core_alternatives = [{"COMP_SCI 262", "IEMS 201", "IEMS 303", "ELEC_ENG 302", "STAT 210"}]

    breadth_courses: Set[str] = set()
    project_courses: Set[str] = set()
    technical_courses: Set[str] = set()
    advanced_intro_support: Set[str] = {"COG_SCI 207", "COMP_ENG 203", "COMP_ENG 205", "COMP_SCI 260", "COMP_SCI 262", "COMP_SCI 296", "COMP_SCI 298", "MECH_ENG 233"}

    section = None
    for line in lines:
        if not line:
            continue
        lower = line.lower()
        if "5 breadth courses chosen" in lower:
            section = "breadth"
            continue
        if "project courses" in lower:
            section = "project"
            continue
        if lower.startswith("technical electives"):
            section = "technical"
            continue
        if section in {"breadth", "project", "technical"}:
            code = extract_course_code_from_line(line)
            if code:
                if section == "breadth":
                    breadth_courses.add(code)
                elif section == "project":
                    project_courses.add(code)
                elif section == "technical":
                    technical_courses.add(code)
    return DegreeRequirements(
        core_required=core_required,
        core_alternatives=core_alternatives,
        breadth_courses=breadth_courses,
        project_courses=project_courses,
        technical_courses=technical_courses,
        advanced_intro_support=advanced_intro_support,
    )


def is_comp_sci_300_plus(code: str) -> bool:
    m = re.search(r"^(COMP_SCI)\s+(\d{3})", code)
    return bool(m and int(m.group(2)) >= 300)


def audit_degree(completed: Set[str], req: DegreeRequirements) -> DegreeAuditResult:
    missing_core = sorted(c for c in req.core_required if c not in completed)
    missing_alternative_groups: List[List[str]] = []
    for group in req.core_alternatives:
        if not (group & completed):
            missing_alternative_groups.append(sorted(group))

    breadth_taken = {c for c in completed if c in req.breadth_courses}
    project_taken = {c for c in completed if c in req.project_courses}
    technical_taken = {
        c
        for c in completed
        if c in req.technical_courses or is_comp_sci_300_plus(c)
    }
    advanced_taken = {
        c
        for c in completed
        if is_comp_sci_300_plus(c) or c in req.advanced_intro_support
    }

    breadth_remaining = max(0, 5 - len(breadth_taken))
    project_remaining = max(0, 2 - len(project_taken))
    technical_remaining = max(0, 6 - len(technical_taken))
    advanced_remaining = max(0, 3 - len(advanced_taken))

    eligible = (
        not missing_core
        and not missing_alternative_groups
        and breadth_remaining == 0
        and project_remaining == 0
        and technical_remaining == 0
        and advanced_remaining == 0
    )

    return DegreeAuditResult(
        graduation_eligible=eligible,
        missing_core=missing_core,
        missing_alternative_groups=missing_alternative_groups,
        breadth_remaining=breadth_remaining,
        project_remaining=project_remaining,
        technical_remaining=technical_remaining,
        advanced_remaining=advanced_remaining,
    )


class PlannerEngine:
    def __init__(self, courses_csv_path: str, degree_md_path: str):
        self.courses_csv_path = courses_csv_path
        self.degree_requirements = parse_degree_requirements(degree_md_path)
        self.catalog: Dict[str, Course] = {}
        self.term_columns: List[str] = []
        self.graph = nx.DiGraph()
        self._load_catalog()

    def _load_catalog(self) -> None:
        with open(self.courses_csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            self.term_columns = [h for h in headers if TERM_PATTERN.match(h or "")]
            for row in reader:
                expanded_codes = expand_course_field(row.get("Course", ""))
                if not expanded_codes:
                    continue
                title = row.get("Course Title", "").strip()
                prereq_text = row.get("Prerequisites", "").strip()
                course_types = {normalize_space(x) for x in (row.get("Course Type", "") or "").split(",") if x.strip()}

                offerings = {t for t in self.term_columns if normalize_space(row.get(t, ""))}
                offered_seasons = {parse_term(t)[0] for t in offerings}
                rule = parse_prereq_rule(prereq_text)
                flags = policy_flags_from_text(prereq_text)

                for code in expanded_codes:
                    if code not in self.catalog:
                        self.catalog[code] = Course(
                            code=code,
                            title=title,
                            offerings=set(),
                            offered_seasons=set(),
                            prereq_text=prereq_text,
                            prereq_rule=rule,
                            policy_flags=set(flags),
                            course_types=set(course_types),
                        )
                    else:
                        self.catalog[code].policy_flags |= flags
                        self.catalog[code].course_types |= course_types
                        if len(prereq_text) > len(self.catalog[code].prereq_text):
                            self.catalog[code].prereq_text = prereq_text
                            self.catalog[code].prereq_rule = rule
                    self.catalog[code].offerings |= offerings
                    self.catalog[code].offered_seasons |= offered_seasons

        self._build_graph()

    def _build_graph(self) -> None:
        for code, course in self.catalog.items():
            self.graph.add_node(code, title=course.title, policy_flags=sorted(course.policy_flags))
            for pre in rule_courses(course.prereq_rule):
                self.graph.add_edge(pre, code)

    def normalize_user_courses(self, courses: Iterable[str]) -> Set[str]:
        normalized: Set[str] = set()
        for c in courses:
            code = normalize_course_code(c)
            if code:
                normalized.add(code)
        return normalized

    def _is_offered(self, course_code: str, term: str) -> bool:
        course = self.catalog.get(course_code)
        if not course:
            return False
        season, _ = parse_term(term)
        return season in course.offered_seasons

    def _eligible_courses(self, completed: Set[str], term: str) -> List[str]:
        eligible: List[str] = []
        for code, course in self.catalog.items():
            if code in completed:
                continue
            if not self._is_offered(code, term):
                continue
            if not evaluate_rule(course.prereq_rule, completed):
                continue
            eligible.append(code)
        return sorted(eligible)

    def _priority_score(self, code: str, target_courses: Set[str], completed: Set[str]) -> int:
        score = 0
        if code in target_courses:
            score += 100
        if code in self.degree_requirements.core_required:
            score += 30
        if code in self.degree_requirements.breadth_courses:
            score += 10
        if code in self.degree_requirements.project_courses:
            score += 10
        if code in self.degree_requirements.technical_courses or is_comp_sci_300_plus(code):
            score += 8
        descendants = nx.descendants(self.graph, code) if code in self.graph else set()
        score += min(20, len(descendants))
        if code in completed:
            score -= 1000
        return score

    def _beam_search_routes(
        self,
        starting_courses: Set[str],
        target_courses: Set[str],
        start_term: str,
        deadline_term: str,
        max_courses_per_term: int = 3,
        beam_width: int = 15,
    ) -> List[Tuple[Dict[str, List[str]], Set[str]]]:
        terms = generate_terms(start_term, deadline_term)
        states: List[Tuple[Dict[str, List[str]], Set[str]]] = [({}, set(starting_courses))]

        for term in terms:
            expanded: List[Tuple[Dict[str, List[str]], Set[str], int]] = []
            for route, completed in states:
                eligible = self._eligible_courses(completed, term)
                eligible = sorted(
                    eligible,
                    key=lambda c: self._priority_score(c, target_courses, completed),
                    reverse=True,
                )[:7]
                combos: List[Tuple[str, ...]] = [()]
                for k in range(1, min(max_courses_per_term, len(eligible)) + 1):
                    combos.extend(itertools.combinations(eligible, k))

                for combo in combos:
                    next_completed = set(completed) | set(combo)
                    next_route = dict(route)
                    next_route[term] = list(combo)
                    score = 0
                    score += len(target_courses & next_completed) * 100
                    score += (50 if audit_degree(next_completed, self.degree_requirements).graduation_eligible else 0)
                    score += len(next_completed)
                    expanded.append((next_route, next_completed, score))

            expanded.sort(key=lambda x: x[2], reverse=True)
            dedup: Dict[frozenset, Tuple[Dict[str, List[str]], Set[str], int]] = {}
            for route, completed, score in expanded:
                key = frozenset(completed)
                if key not in dedup or score > dedup[key][2]:
                    dedup[key] = (route, completed, score)
            states = [(r, c) for r, c, _ in sorted(dedup.values(), key=lambda x: x[2], reverse=True)[:beam_width]]
        return states

    def _missing_target_blockers(self, completed: Set[str], target_courses: Set[str]) -> List[str]:
        blockers: List[str] = []
        for target in sorted(target_courses):
            if target in completed:
                continue
            if target not in self.catalog:
                blockers.append(f"{target}: not found in catalog")
                continue
            prereq = self.catalog[target].prereq_rule
            missing = sorted(c for c in rule_courses(prereq) if c not in completed)
            if missing:
                blockers.append(f"{target}: missing prerequisites {', '.join(missing)}")
            else:
                blockers.append(f"{target}: not offered in needed term window")
        return blockers

    def _find_earliest_target_term(self, completed: Set[str], target_courses: Set[str], start_term: str, horizon_terms: int = 12) -> Optional[str]:
        cur = start_term
        best_term: Optional[str] = None
        known = set(completed)
        for _ in range(horizon_terms):
            eligible = self._eligible_courses(known, cur)
            for c in eligible:
                known.add(c)
            if target_courses.issubset(known):
                best_term = cur
                break
            cur = next_term(cur)
        return best_term

    def _find_earliest_grad_term(self, completed: Set[str], start_term: str, horizon_terms: int = 16) -> Optional[str]:
        cur = start_term
        known = set(completed)
        for _ in range(horizon_terms):
            eligible = self._eligible_courses(known, cur)
            scored = sorted(eligible, key=lambda c: self._priority_score(c, set(), known), reverse=True)[:3]
            known.update(scored)
            if audit_degree(known, self.degree_requirements).graduation_eligible:
                return cur
            cur = next_term(cur)
        return None

    def plan(
        self,
        completed_courses: Sequence[str],
        target_courses: Sequence[str],
        start_term: str,
        graduation_term: str,
    ) -> PlanResult:
        completed = self.normalize_user_courses(completed_courses)
        targets = self.normalize_user_courses(target_courses)

        states = self._beam_search_routes(
            starting_courses=completed,
            target_courses=targets,
            start_term=start_term,
            deadline_term=graduation_term,
        )
        feasible_routes: List[Dict[str, List[str]]] = []
        final_audit = audit_degree(completed, self.degree_requirements)

        for route, final_completed in states:
            audit = audit_degree(final_completed, self.degree_requirements)
            final_audit = audit
            if targets.issubset(final_completed) and audit.graduation_eligible:
                feasible_routes.append(route)

        if feasible_routes:
            return PlanResult(
                feasible=True,
                message=f"Found {len(feasible_routes)} feasible route(s) for target courses and graduation deadline.",
                routes=feasible_routes[:5],
                blockers=[],
                alternatives={},
                degree_audit=final_audit,
            )

        best_state_completed = states[0][1] if states else set(completed)
        blockers = self._missing_target_blockers(best_state_completed, targets)
        best_audit = audit_degree(best_state_completed, self.degree_requirements)
        alt_target_term = self._find_earliest_target_term(completed, targets, start_term)
        alt_grad_term = self._find_earliest_grad_term(completed, start_term)

        alternatives: Dict[str, str] = {}
        if alt_target_term:
            alternatives["earliest_target_term"] = alt_target_term
        if alt_grad_term:
            alternatives["earliest_graduation_term"] = alt_grad_term
        if not alternatives:
            alternatives["note"] = "No feasible alternative found in the planning horizon."

        return PlanResult(
            feasible=False,
            message="No feasible route found by the requested graduation term.",
            routes=[],
            blockers=blockers,
            alternatives=alternatives,
            degree_audit=best_audit,
        )

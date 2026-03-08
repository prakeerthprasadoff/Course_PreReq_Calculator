from pathlib import Path

from planner_engine import (
    PlannerEngine,
    extract_course_codes_with_context,
    normalize_course_code,
    parse_prereq_rule,
    rule_courses,
)


def _write_fixture_files(tmp_path: Path) -> tuple[str, str]:
    csv_content = """Course,Course Title,Fall 2025,Winter 2026,Spring 2026,Summer 2026,Extracted_Link,Prerequisites,Course Type
COMP_SCI 111,Intro,,,X,,,,
COMP_SCI 150,Fundamentals,X,,,,"","",Core Requirement
COMP_SCI 211,Prog II,,X,,,"","COMP_SCI 111, 150",Core Requirement
COMP_SCI 213,Systems,,,X,,"","COMP_SCI 211",Core Requirement
COMP_SCI 214,DSA,X,X,X,,"","COMP_SCI 211",Core Requirement
COMP_SCI 340,Networking,X,,X,,"","COMP_SCI 214","Breadth: Systems, Technical Elective"
COMP_SCI 343,OS,,X,,,"","COMP_SCI 214","Breadth: Systems, Project Course"
COMP_SCI 349,Machine Learning,,,X,,"","COMP_SCI 214","Breadth: Artificial Intelligence, Technical Elective"
"""
    md_content = """5 required courses -
COMP_SCI 150-0
COMP_SCI 211-0
COMP_SCI 213-0
COMP_SCI 214-0
COMP_SCI 262-0
or IEMS 201-0
or IEMS 303-0
or ELEC_ENG 302-0
or STAT 210-0

3 advanced elective courses
Any 300-level or higher class, or introductory courses that directly support computer science (COG_SCI 207-0, COMP_ENG 203-0)

5 breadth courses chosen from the options below -
Theory
COMP_SCI 335-0
Systems
COMP_SCI 340-0
COMP_SCI 343-0
Artificial Intelligence
COMP_SCI 349-0

Project Courses
Majors must take two courses from this list -
COMP_SCI 343-0

Technical electives
Majors must take six technical electives.
COMP_SCI 340-0
COMP_SCI 349-0
"""
    csv_path = tmp_path / "courses.csv"
    md_path = tmp_path / "degree.md"
    csv_path.write_text(csv_content, encoding="utf-8")
    md_path.write_text(md_content, encoding="utf-8")
    return str(csv_path), str(md_path)


def test_normalize_course_code():
    assert normalize_course_code("cs 214") == "COMP_SCI 214"
    assert normalize_course_code("COMP_SCI 316-1") == "COMP_SCI 316-1"
    assert normalize_course_code("214", default_dept="COMP_SCI") == "COMP_SCI 214"


def test_prereq_parsing_courses():
    rule = parse_prereq_rule("COMP_SCI 111, 150")
    courses = rule_courses(rule)
    assert "COMP_SCI 111" in courses
    assert "COMP_SCI 150" in courses
    extracted = extract_course_codes_with_context("CS 214, IEMS 201, STAT 210")
    assert "COMP_SCI 214" in extracted
    assert "IEMS 201" in extracted


def test_planner_feasibility_and_fallback(tmp_path: Path):
    csv_path, md_path = _write_fixture_files(tmp_path)
    engine = PlannerEngine(csv_path, md_path)

    feasible = engine.plan(
        completed_courses=["COMP_SCI 111", "COMP_SCI 150", "COMP_SCI 211", "COMP_SCI 214"],
        target_courses=["COMP_SCI 340"],
        start_term="Fall 2025",
        graduation_term="Spring 2026",
    )
    assert feasible.message
    assert isinstance(feasible.feasible, bool)

    infeasible = engine.plan(
        completed_courses=["COMP_SCI 111"],
        target_courses=["COMP_SCI 340"],
        start_term="Fall 2025",
        graduation_term="Fall 2025",
    )
    assert not infeasible.feasible
    assert infeasible.alternatives

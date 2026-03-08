import streamlit as st
import re
from pathlib import Path
from dataclasses import asdict
from typing import Dict, List, Set
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

from planner_engine import PlannerEngine, term_sort_key, rule_courses
from azure_llm_client import AzureLLMClient, load_azure_llm_config
from track_recommender import (
    build_track_payload,
    derive_tracks_from_engine,
    generate_final_track_plan,
    recommendation_to_dict,
    recommend_tracks,
)

# Page configuration
st.set_page_config(
    page_title="PIED PIPER - Course Planner",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for green theme
st.markdown("""
    <style>
    :root {
        --pp-text-primary: #1f3d2b;
        --pp-text-secondary: #2d5f3f;
    }

    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #f6fbf8 0%, #edf7f1 100%);
        color: var(--pp-text-primary);
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: var(--pp-text-secondary) !important;
    }

    p, li, label, span, div[data-testid="stMarkdownContainer"] {
        color: var(--pp-text-primary);
    }
    
    .block-container {
        max-width: 1200px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #4a8b5f;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 10px 22px;
        font-weight: 600;
        font-size: 15px;
    }
    
    .stButton > button:hover {
        background-color: #3d7350;
    }
    
    .stButton > button:disabled {
        background-color: #c5dccf;
        color: #f8fffb;
    }
    
    .stCheckbox {
        padding: 10px 12px;
        border-radius: 10px;
        border: 1px solid #d7e7de;
        background: #ffffff;
        margin-bottom: 8px;
    }

    /* Force readable checkbox label text */
    .stCheckbox label,
    .stCheckbox [data-testid="stMarkdownContainer"],
    .stCheckbox [data-testid="stMarkdownContainer"] p,
    .stCheckbox [data-testid="stMarkdownContainer"] span {
        color: #1f3d2b !important;
        opacity: 1 !important;
    }
    
    /* Info boxes */
    .stAlert {
        background-color: #e8f5ed;
        border-left: 4px solid #4a8b5f;
        color: var(--pp-text-primary);
    }

    .stInfo, .stWarning, .stError, .stSuccess {
        color: var(--pp-text-primary) !important;
    }

    .stInfo p, .stWarning p, .stError p, .stSuccess p {
        color: var(--pp-text-primary) !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f5faf7;
        border-radius: 12px;
        color: #2d5f3f;
    }
    
    /* Text Area */
    .stTextArea textarea {
        border: 1px solid #cfe0d7 !important;
        border-radius: 12px !important;
        background-color: white !important;
        color: #2d5f3f !important;
    }
    
    .stTextArea label {
        color: var(--pp-text-secondary) !important;
        font-weight: 600 !important;
    }
    
    /* File Uploader */
    .stFileUploader {
        padding: 12px;
        background: white;
        border-radius: 12px;
        border: 1px dashed #cfe0d7;
        margin-bottom: 12px;
    }

    .pp-section {
        background: rgba(255,255,255,0.75);
        border: 1px solid #dbe9e2;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 14px;
    }

    .stCaption {
        color: var(--pp-text-secondary) !important;
    }
    </style>
""", unsafe_allow_html=True)

# Catalog + degree engine
BASE_DIR = Path(__file__).resolve().parent
COURSE_CSV = str(BASE_DIR / "main_course_info_typed.csv")
DEGREE_MD = str(BASE_DIR / "BS_Mccormick_CS.md")
ENGINE = PlannerEngine(COURSE_CSV, DEGREE_MD)
TRACK_TO_COURSES, COURSE_TO_TRACKS = derive_tracks_from_engine(ENGINE)
LLM_CLIENT = AzureLLMClient(load_azure_llm_config())

COURSES_COMPLETED = sorted(
    [{"code": c.code, "name": c.title or c.code, "credits": 1} for c in ENGINE.catalog.values()],
    key=lambda x: x["code"],
)
COURSES_AVAILABLE = sorted(
    [
        {
            "code": c.code,
            "name": c.title or c.code,
            "credits": 1,
            "prereq": c.prereq_text,
        }
        for c in ENGINE.catalog.values()
    ],
    key=lambda x: x["code"],
)

COURSE_NAME_BY_CODE = {c["code"]: c["name"] for c in COURSES_AVAILABLE}


def course_label(code: str) -> str:
    title = COURSE_NAME_BY_CODE.get(code, "")
    return f"{code} - {title}" if title else code


def build_route_graph_dot(
    route: Dict[str, List[str]],
    completed_courses: Set[str],
    desired_courses: Set[str],
) -> str:
    route_courses: Set[str] = set()
    for courses in route.values():
        route_courses.update(courses)

    lines: List[str] = [
        "digraph CoursePlan {",
        'rankdir="LR";',
        'bgcolor="transparent";',
        'node [shape=box, style="rounded,filled", fillcolor="#f5faf7", color="#4a8b5f", fontname="Helvetica"];',
        'edge [color="#7ba88c"];',
    ]

    # Only course nodes and prerequisite relations (no term/timeline nodes).
    for course in sorted(route_courses):
        course_fill = "#fff4d6" if course in desired_courses else "#f5faf7"
        lines.append(f'"{course}" [label="{course}", fillcolor="{course_fill}"];')

    # Prerequisite edges among planned + completed context.
    for course in sorted(route_courses):
        catalog_course = ENGINE.catalog.get(course)
        if not catalog_course:
            continue
        prereqs = rule_courses(catalog_course.prereq_rule)
        for pre in sorted(prereqs):
            if pre in route_courses:
                lines.append(f"\"{pre}\" -> \"{course}\";")
            elif pre in completed_courses:
                lines.append(f'"{pre}" [label="{pre}\\n(completed)", fillcolor="#dff3e5", color="#4a8b5f"];')
                lines.append(f"\"{pre}\" -> \"{course}\" [style=dashed];")

    lines.append("}")
    return "\n".join(lines)


@st.dialog("Course Route Graph")
def show_course_graph_dialog(route: Dict[str, List[str]], route_label: str) -> None:
    st.markdown(f"**{route_label}**")
    dot = build_route_graph_dot(
        route=route,
        completed_courses=set(st.session_state.completed_courses),
        desired_courses=set(st.session_state.desired_courses),
    )
    st.graphviz_chart(dot, use_container_width=True)
    st.caption("Yellow nodes are desired courses. Green dashed prerequisite nodes are already completed.")


# Initialize session state
if 'completed_courses' not in st.session_state:
    st.session_state.completed_courses = []
if 'desired_courses' not in st.session_state:
    st.session_state.desired_courses = []
if 'completed_dropdown' not in st.session_state:
    st.session_state.completed_dropdown = []
if 'desired_dropdown' not in st.session_state:
    st.session_state.desired_dropdown = []
if 'generated_plan' not in st.session_state:
    st.session_state.generated_plan = None
if 'track_recommendation' not in st.session_state:
    st.session_state.track_recommendation = None
if 'selected_track' not in st.session_state:
    st.session_state.selected_track = None
if 'final_track_plan' not in st.session_state:
    st.session_state.final_track_plan = None
if 'graph_route_index' not in st.session_state:
    st.session_state.graph_route_index = 1
if 'start_term' not in st.session_state:
    st.session_state.start_term = "Spring 2026"
if 'graduation_term' not in st.session_state:
    st.session_state.graduation_term = "Spring 2027"

# Header with logo
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # SVG Logo
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <svg width="70" height="70" viewBox="0 0 70 70" fill="none" xmlns="http://www.w3.org/2000/svg" style="display: inline-block;">
                <circle cx="35" cy="35" r="33" fill="#2d5f3f" opacity="0.08"/>
                <path d="M25 28 Q20 35 22 45 L28 44 Q26 36 27 30 Z" fill="#5fa87a" opacity="0.6"/>
                <ellipse cx="30" cy="38" rx="5" ry="9" fill="#2d5f3f"/>
                <circle cx="30" cy="26" r="4.5" fill="#4a8b5f"/>
                <ellipse cx="30" cy="23" rx="5" ry="2.5" fill="#2d5f3f"/>
                <path d="M33 22 Q37 18 36 23 Q35 21 33 22 Z" fill="#5fa87a"/>
                <path d="M26 32 L22 34" stroke="#4a8b5f" stroke-width="2.5" stroke-linecap="round"/>
                <path d="M30 30 L34 28" stroke="#4a8b5f" stroke-width="2.5" stroke-linecap="round"/>
                <rect x="20" y="27.5" width="28" height="2" rx="1" fill="#7ba88c"/>
                <rect x="47" y="27.5" width="3" height="2" rx="1" fill="#7ba88c"/>
                <circle cx="23" cy="28.5" r="1.2" fill="#2d5f3f"/>
                <circle cx="28" cy="28.5" r="1.2" fill="#2d5f3f"/>
                <circle cx="33" cy="28.5" r="1.2" fill="#2d5f3f"/>
                <circle cx="38" cy="28.5" r="1.2" fill="#2d5f3f"/>
                <circle cx="43" cy="28.5" r="1.2" fill="#2d5f3f"/>
                <text x="50" y="22" fill="#4a8b5f" font-size="8" opacity="0.7">♪</text>
                <text x="52" y="35" fill="#5fa87a" font-size="7" opacity="0.6">♫</text>
                <text x="48" y="40" fill="#4a8b5f" font-size="6" opacity="0.5">♪</text>
                <circle cx="45" cy="24" r="1" fill="#7ba88c" opacity="0.8"/>
                <circle cx="50" cy="30" r="0.8" fill="#5fa87a" opacity="0.7"/>
                <circle cx="47" cy="36" r="1.2" fill="#4a8b5f" opacity="0.6"/>
            </svg>
            <h1 style="margin-top: 10px; margin-bottom: 5px; color: #2d5f3f; letter-spacing: 2px;">PIED PIPER</h1>
            <p style="font-style: italic; color: #5a8169; margin-top: 0;">The first in middle-out course planning</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Section 1: Completed Courses
st.markdown("### 📚 Courses Completed")

# Synchronization logic for Completed Courses
if 'completed_bulk_text' not in st.session_state:
    st.session_state.completed_bulk_text = ", ".join(st.session_state.completed_courses)

def on_completed_text_change():
    input_text = st.session_state.completed_bulk_text
    codes = [c.strip() for c in input_text.replace('\n', ',').split(',') if c.strip()]
    normalized = sorted(ENGINE.normalize_user_courses(codes))
    st.session_state.completed_courses = normalized
    st.session_state.completed_dropdown = normalized


def on_completed_dropdown_change():
    selected = sorted(set(st.session_state.completed_dropdown))
    st.session_state.completed_courses = selected
    st.session_state.completed_bulk_text = ", ".join(selected)

# Transcript Upload Logic
def extract_courses_from_text(text):
    # Regex for department + 3-digit course patterns.
    pattern = r'[A-Z_]{2,12}\s?-?\s?\d{3}(?:-\d)?'
    matches = re.findall(pattern, text.upper())
    normalized = sorted(ENGINE.normalize_user_courses(matches))
    return normalized

uploaded_file = st.file_uploader(
    "📄 Upload your transcript to auto-fill courses",
    type=["pdf", "txt"],
    help="Upload a PDF or TXT transcript. We'll scan it for course codes like CS 101."
)

if uploaded_file is not None:
    text_content = ""
    try:
        if uploaded_file.type == "application/pdf":
            if PdfReader:
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    text_content += page.extract_text()
            else:
                st.error("PDF processing library (pypdf) not installed. Please try a .txt file or paste manually.")
        else:
            text_content = uploaded_file.read().decode("utf-8")
        
        if text_content:
            found_courses = extract_courses_from_text(text_content)
            if found_courses:
                # Filter to only include courses we know about OR allow all? 
                # User asked to upload rather than manually filling, implying they want all recognized ones.
                # Let's add them to the session state.
                st.session_state.completed_courses = list(set(st.session_state.completed_courses + found_courses))
                st.session_state.completed_bulk_text = ", ".join(st.session_state.completed_courses)
                st.session_state.completed_dropdown = sorted(st.session_state.completed_courses)
                st.success(f"Successfully extracted {len(found_courses)} courses from transcript!")
            else:
                st.warning("No course codes were recognized in the uploaded file.")
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

st.text_area(
    "Type courses you've taken (e.g., CS 101, MATH 220)",
    key="completed_bulk_text",
    on_change=on_completed_text_change,
    placeholder="CS 101, CS 201...",
    help="You can type course codes separated by commas or new lines. The blocks below will update automatically."
)

st.markdown("#### Or select from dropdown:")
if sorted(st.session_state.completed_dropdown) != sorted(st.session_state.completed_courses):
    st.session_state.completed_dropdown = sorted(st.session_state.completed_courses)
st.multiselect(
    "Completed courses dropdown",
    options=[c["code"] for c in COURSES_COMPLETED],
    format_func=course_label,
    key="completed_dropdown",
    on_change=on_completed_dropdown_change,
    label_visibility="collapsed",
)

st.markdown(f"*{len(st.session_state.completed_courses)} course(s) recognized*")
st.markdown("---")

# Section 2: Desired Courses
st.markdown("### 📖 Desired Courses")

# Synchronization logic for Desired Courses
if 'desired_bulk_text' not in st.session_state:
    st.session_state.desired_bulk_text = ", ".join(st.session_state.desired_courses)


def on_desired_text_change():
    input_text = st.session_state.desired_bulk_text
    codes = [c.strip() for c in input_text.replace('\n', ',').split(',') if c.strip()]
    normalized = sorted(ENGINE.normalize_user_courses(codes))
    st.session_state.desired_courses = normalized
    st.session_state.desired_dropdown = normalized


def on_desired_dropdown_change():
    selected = sorted(set(st.session_state.desired_dropdown))
    st.session_state.desired_courses = selected
    st.session_state.desired_bulk_text = ", ".join(selected)

st.text_area(
    "Type courses you want to take",
    key="desired_bulk_text",
    on_change=on_desired_text_change,
    placeholder="CS 370, CS 380...",
    help="Type course codes separated by commas or new lines."
)

st.markdown("#### Or select from dropdown:")
if sorted(st.session_state.desired_dropdown) != sorted(st.session_state.desired_courses):
    st.session_state.desired_dropdown = sorted(st.session_state.desired_courses)
st.multiselect(
    "Desired courses dropdown",
    options=[c["code"] for c in COURSES_AVAILABLE],
    format_func=course_label,
    key="desired_dropdown",
    on_change=on_desired_dropdown_change,
    label_visibility="collapsed",
)

st.markdown(f"*{len(st.session_state.desired_courses)} course(s) selected*")
st.markdown("---")

# Section 3: Generate Plan
st.markdown("### ✨ Ready to Generate Your Plan?")

col_left, col_mid, col_right = st.columns([1, 2, 1])
with col_mid:
    st.markdown(f"""
        <div style="text-align: center; margin: 20px 0;">
            <p style="color: #5a8169; font-size: 15px;">
                {len(st.session_state.completed_courses)} completed · {len(st.session_state.desired_courses)} desired
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.caption(f"Planning start term (auto): **{st.session_state.start_term}**")
    graduation_options = sorted(set(ENGINE.term_columns), key=term_sort_key)
    if st.session_state.graduation_term not in graduation_options:
        graduation_options.append(st.session_state.graduation_term)
        graduation_options = sorted(set(graduation_options), key=term_sort_key)
    grad_index = graduation_options.index(st.session_state.graduation_term) if st.session_state.graduation_term in graduation_options else 0
    st.session_state.graduation_term = st.selectbox(
        "Target graduation term",
        options=graduation_options,
        index=grad_index,
    )

    valid_term_order = term_sort_key(st.session_state.start_term) <= term_sort_key(st.session_state.graduation_term)
    can_generate = (
        len(st.session_state.completed_courses) > 0
        and len(st.session_state.desired_courses) > 0
        and valid_term_order
    )

    if st.button("✨ Generate My Course Plan", disabled=not can_generate, use_container_width=True):
        with st.spinner("Building feasible routes from prerequisites and quarter offerings..."):
            try:
                result = ENGINE.plan(
                    completed_courses=st.session_state.completed_courses,
                    target_courses=st.session_state.desired_courses,
                    start_term=st.session_state.start_term,
                    graduation_term=st.session_state.graduation_term,
                )
                st.session_state.generated_plan = result
                st.session_state.track_recommendation = None
                st.session_state.selected_track = None
                st.session_state.final_track_plan = None

                if result.feasible and result.routes:
                    payload = build_track_payload(
                        completed_courses=st.session_state.completed_courses,
                        desired_courses=st.session_state.desired_courses,
                        graduation_term=st.session_state.graduation_term,
                        routes=result.routes,
                        track_to_courses=TRACK_TO_COURSES,
                    )
                    recommendation = recommend_tracks(LLM_CLIENT, payload)
                    st.session_state.track_recommendation = recommendation_to_dict(recommendation)
            except Exception as exc:
                st.error(f"Could not generate plan: {exc}")

    if not valid_term_order:
        st.warning("Target graduation term must be the same as or after planning start term.")
    if not can_generate and valid_term_order:
        st.markdown("""
            <p style="color: #7ba88c; font-size: 13px; font-style: italic; text-align: center;">
                Please select at least one completed and one desired course
            </p>
        """, unsafe_allow_html=True)

st.markdown("---")

# Section 4: Generated Plan (only shows after generation)
if st.session_state.generated_plan is not None:
    result = st.session_state.generated_plan
    st.markdown("### 📅 Your Course Plan")
    st.info(result.message)
    if LLM_CLIENT.available:
        st.caption("LLM mode: Azure-connected track recommendations enabled.")
    else:
        st.caption("LLM mode: Azure not configured, using deterministic track fallback.")

    if result.feasible:
        desired_set = set(st.session_state.desired_courses)
        completed_set = set(st.session_state.completed_courses)
        already_completed_desired = sorted(desired_set & completed_set)

        graph_col1, graph_col2 = st.columns([2, 1])
        with graph_col1:
            st.session_state.graph_route_index = st.selectbox(
                "Route to visualize",
                options=list(range(1, len(result.routes) + 1)),
                index=min(len(result.routes), max(1, st.session_state.graph_route_index)) - 1,
                help="Choose which feasible route to render as a course graph.",
            )
        with graph_col2:
            st.write("")
            st.write("")
            if st.button("🕸 View Course Graph", use_container_width=True):
                idx = st.session_state.graph_route_index
                route = result.routes[idx - 1]
                show_course_graph_dialog(route, f"Feasible Route {idx}")

        if already_completed_desired:
            st.markdown(
                f"**Desired courses already completed:** {', '.join(already_completed_desired)}"
            )

        for i, route in enumerate(result.routes, start=1):
            route_courses = set()
            for courses in route.values():
                route_courses.update(courses)
            desired_in_route = sorted(desired_set & route_courses)

            with st.expander(f"Feasible Route {i}", expanded=(i == 1)):
                if desired_in_route:
                    st.markdown(f"**Desired courses scheduled in this route:** {', '.join(desired_in_route)}")
                elif desired_set and already_completed_desired:
                    st.markdown("**Desired-course note:** Desired courses are already satisfied from completed history.")
                for term in sorted(route.keys(), key=term_sort_key):
                    courses = route.get(term, [])
                    if not courses:
                        continue
                    rendered = []
                    for course in courses:
                        if course in desired_set:
                            rendered.append(f"⭐ {course}")
                        else:
                            rendered.append(course)
                    st.markdown(f"**{term}**: {', '.join(rendered)}")

        track_rec = st.session_state.track_recommendation or {}
        track_options = track_rec.get("track_options", [])
        if track_options:
            st.markdown("### Suggested Track Plans")
            if track_rec.get("recommended_track"):
                st.markdown(f"**Recommended track:** {track_rec['recommended_track']}")
            if track_rec.get("notes"):
                st.caption(track_rec["notes"])

            cols = st.columns(min(3, max(1, len(track_options))))
            for idx, option in enumerate(track_options):
                with cols[idx % len(cols)]:
                    label = f"{option['track']} ({option['confidence']:.2f})"
                    if st.button(label, key=f"track_btn_{option['track']}_{idx}", use_container_width=True):
                        st.session_state.selected_track = option["track"]
                        final_plan = generate_final_track_plan(
                            llm_client=LLM_CLIENT,
                            selected_track=option["track"],
                            feasible_routes=result.routes,
                            route_hint=int(option.get("aligned_route_index", 1)),
                        )
                        st.session_state.final_track_plan = asdict(final_plan)

            if st.session_state.selected_track and st.session_state.final_track_plan:
                st.markdown(f"### Final Plan for {st.session_state.selected_track}")
                st.markdown(st.session_state.final_track_plan.get("final_plan_markdown", ""))
                notes = st.session_state.final_track_plan.get("notes", "")
                if notes:
                    st.caption(notes)
    else:
        st.error("Requested graduation timeline is infeasible with current constraints.")
        if result.blockers:
            st.markdown("**Blockers:**")
            for blocker in result.blockers:
                st.markdown(f"- {blocker}")
        if result.alternatives:
            st.markdown("**Alternatives:**")
            for key, value in result.alternatives.items():
                st.markdown(f"- {key.replace('_', ' ').title()}: {value}")

    audit = result.degree_audit
    st.markdown("### Degree Audit Snapshot")
    st.markdown(f"- Missing core courses: {', '.join(audit.missing_core) if audit.missing_core else 'None'}")
    if audit.missing_alternative_groups:
        for group in audit.missing_alternative_groups:
            st.markdown(f"- Need one from: {', '.join(group)}")
    st.markdown(f"- Breadth courses remaining: {audit.breadth_remaining}")
    st.markdown(f"- Project courses remaining: {audit.project_remaining}")
    st.markdown(f"- Technical electives remaining: {audit.technical_remaining}")
    st.markdown(f"- Advanced electives remaining: {audit.advanced_remaining}")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state.completed_courses = []
            st.session_state.desired_courses = []
            st.session_state.completed_bulk_text = ""
            st.session_state.desired_bulk_text = ""
            st.session_state.generated_plan = None
            st.session_state.track_recommendation = None
            st.session_state.selected_track = None
            st.session_state.final_track_plan = None
            st.rerun()
    with col2:
        st.button("📥 Export Plan", use_container_width=True, disabled=True)

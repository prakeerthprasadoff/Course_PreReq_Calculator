import streamlit as st
import time
import re
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

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
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #f0f9f4 0%, #e8f5ed 100%);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #2d5f3f !important;
    }
    
    /* Card styling */
    .stMarkdown div[data-testid="stMarkdownContainer"] {
        color: #5a8169;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #4a8b5f;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 14px 32px;
        font-weight: 600;
        font-size: 15px;
    }
    
    .stButton > button:hover {
        background-color: #3d7350;
    }
    
    .stButton > button:disabled {
        background-color: #c5dccf;
        color: white;
    }
    
    /* Checkbox styling */
    .stCheckbox {
        padding: 16px 20px;
        border-radius: 12px;
        border: 2px solid #d4e5db;
        background: white;
        margin-bottom: 12px;
    }
    
    /* Info boxes */
    .stAlert {
        background-color: #e8f5ed;
        border-left: 4px solid #4a8b5f;
        color: #3d6b4f;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f5faf7;
        border-radius: 12px;
        color: #2d5f3f;
    }
    
    /* Text Area */
    .stTextArea textarea {
        border: 2px solid #d4e5db !important;
        border-radius: 12px !important;
        background-color: white !important;
        color: #2d5f3f !important;
    }
    
    .stTextArea label {
        color: #2d5f3f !important;
        font-weight: 600 !important;
    }
    
    /* File Uploader */
    .stFileUploader {
        padding: 20px;
        background: white;
        border-radius: 12px;
        border: 2px dashed #d4e5db;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Sample CS courses database (Sorted)
COURSES_COMPLETED = sorted([
    {"code": "CS 101", "name": "Intro to Computer Science", "credits": 3},
    {"code": "CS 201", "name": "Data Structures", "credits": 4},
    {"code": "MATH 220", "name": "Calculus I", "credits": 4},
    {"code": "MATH 221", "name": "Calculus II", "credits": 4},
], key=lambda x: x['code'])

COURSES_AVAILABLE = sorted([
    {"code": "CS 202", "name": "Algorithms", "credits": 4, "prereq": "CS 201"},
    {"code": "CS 301", "name": "Operating Systems", "credits": 3, "prereq": "CS 201"},
    {"code": "CS 340", "name": "Database Systems", "credits": 3, "prereq": "CS 201"},
    {"code": "CS 351", "name": "Computer Networks", "credits": 3, "prereq": "CS 201"},
    {"code": "CS 370", "name": "Artificial Intelligence", "credits": 3, "prereq": "CS 202"},
    {"code": "CS 380", "name": "Machine Learning", "credits": 3, "prereq": "CS 202"},
    {"code": "CS 420", "name": "Software Engineering", "credits": 3, "prereq": "CS 301"},
    {"code": "CS 450", "name": "Computer Graphics", "credits": 3, "prereq": "CS 202"},
    {"code": "CS 461", "name": "Cybersecurity", "credits": 3, "prereq": "CS 351"},
    {"code": "CS 490", "name": "Senior Capstone", "credits": 4, "prereq": "Senior Standing"},
], key=lambda x: x['code'])

# Initialize session state
if 'completed_courses' not in st.session_state:
    st.session_state.completed_courses = []
if 'desired_courses' not in st.session_state:
    st.session_state.desired_courses = []
if 'generated_plan' not in st.session_state:
    st.session_state.generated_plan = None

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
    # Parse comma or newline separated codes
    codes = [c.strip().upper() for c in input_text.replace('\n', ',').split(',') if c.strip()]
    st.session_state.completed_courses = list(set(codes)) # Remove duplicates

def on_completed_checkbox_change(course_code):
    is_checked = st.session_state[f"completed_{course_code}"]
    if is_checked:
        if course_code not in st.session_state.completed_courses:
            st.session_state.completed_courses.append(course_code)
    else:
        if course_code in st.session_state.completed_courses:
            st.session_state.completed_courses.remove(course_code)
    # Sync back to text area
    st.session_state.completed_bulk_text = ", ".join(st.session_state.completed_courses)

# Transcript Upload Logic
def extract_courses_from_text(text):
    # Regex to find common course pattern (e.g., CS 101, MATH 220, CS101)
    pattern = r'[A-Z]{2,4}\s?\d{3,4}'
    matches = re.findall(pattern, text.upper())
    # Normalize matches (add space if missing)
    normalized = []
    for match in matches:
        if not re.search(r'\s', match):
            # Split alpha and numeric
            m = re.match(r'([A-Z]+)(\d+)', match)
            if m:
                normalized.append(f"{m.group(1)} {m.group(2)}")
        else:
            normalized.append(match)
    return list(set(normalized))

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

st.markdown("#### Or select from common courses:")

# Create columns for completed courses
cols = st.columns(3)
for idx, course in enumerate(COURSES_COMPLETED):
    with cols[idx % 3]:
        is_selected = course['code'] in st.session_state.completed_courses
        st.checkbox(
            f"**{course['code']}**\n{course['name']}\n({course['credits']} cr)",
            key=f"completed_{course['code']}",
            value=is_selected,
            on_change=on_completed_checkbox_change,
            args=(course['code'],)
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
    codes = [c.strip().upper() for c in input_text.replace('\n', ',').split(',') if c.strip()]
    st.session_state.desired_courses = codes

def on_desired_checkbox_change(course_code):
    is_checked = st.session_state[f"desired_{course_code}"]
    if is_checked:
        if course_code not in st.session_state.desired_courses:
            st.session_state.desired_courses.append(course_code)
    else:
        if course_code in st.session_state.desired_courses:
            st.session_state.desired_courses.remove(course_code)
    # Sync back to text area
    st.session_state.desired_bulk_text = ", ".join(st.session_state.desired_courses)

st.text_area(
    "Type courses you want to take",
    key="desired_bulk_text",
    on_change=on_desired_text_change,
    placeholder="CS 370, CS 380...",
    help="Type course codes separated by commas or new lines."
)

st.markdown("#### Or select from available courses:")

# Create columns for desired courses
cols = st.columns(3)
for idx, course in enumerate(COURSES_AVAILABLE):
    with cols[idx % 3]:
        is_selected = course['code'] in st.session_state.desired_courses
        label = f"**{course['code']}**\n{course['name']}\n({course['credits']} cr)"
        if 'prereq' in course:
            label += f"\n\n*Prereq: {course['prereq']}*"
        
        st.checkbox(
            label,
            key=f"desired_{course['code']}",
            value=is_selected,
            on_change=on_desired_checkbox_change,
            args=(course['code'],)
        )

st.markdown(f"*{len(st.session_state.desired_courses)} course(s) selected*")
st.markdown("---")

# Section 3: Generate Plan
st.markdown("### ✨ Ready to Generate Your Plan?")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown(f"""
        <div style="text-align: center; margin: 20px 0;">
            <p style="color: #5a8169; font-size: 15px;">
                {len(st.session_state.completed_courses)} completed · {len(st.session_state.desired_courses)} desired
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    can_generate = len(st.session_state.completed_courses) > 0 and len(st.session_state.desired_courses) > 0
    
    if st.button("✨ Generate My Course Plan", disabled=not can_generate, use_container_width=True):
        with st.spinner("Generating your personalized course plan..."):
            time.sleep(2)  # Simulate LLM processing
            
            # Get full course objects for desired courses
            desired_course_objects = [c for c in COURSES_AVAILABLE if c['code'] in st.session_state.desired_courses]
            
            # Generate mock plan
            quarters = []
            if len(desired_course_objects) > 0:
                quarters.append({
                    'name': 'Fall 2024',
                    'courses': desired_course_objects[0:3],
                    'credits': sum(c['credits'] for c in desired_course_objects[0:3])
                })
            if len(desired_course_objects) > 3:
                quarters.append({
                    'name': 'Winter 2025',
                    'courses': desired_course_objects[3:6],
                    'credits': sum(c['credits'] for c in desired_course_objects[3:6])
                })
            if len(desired_course_objects) > 6:
                quarters.append({
                    'name': 'Spring 2025',
                    'courses': desired_course_objects[6:9],
                    'credits': sum(c['credits'] for c in desired_course_objects[6:9])
                })
            
            st.session_state.generated_plan = {
                'quarters': quarters,
                'total_credits': sum(c['credits'] for c in desired_course_objects),
                'recommendation': "This plan balances core requirements with your AI/ML focus. Consider CS 202 early as it unlocks several advanced courses."
            }
    
    if not can_generate:
        st.markdown("""
            <p style="color: #7ba88c; font-size: 13px; font-style: italic; text-align: center;">
                Please select at least one completed and one desired course
            </p>
        """, unsafe_allow_html=True)

st.markdown("---")

# Section 4: Generated Plan (only shows after generation)
if st.session_state.generated_plan is not None:
    st.markdown("### 📅 Your Course Plan")
    
    # AI Recommendation
    st.info(f"**✨ AI Recommendation**\n\n{st.session_state.generated_plan['recommendation']}")
    
    # Quarter-by-quarter plan
    for quarter in st.session_state.generated_plan['quarters']:
        with st.expander(f"**{quarter['name']}** - {quarter['credits']} credits", expanded=True):
            cols = st.columns(3)
            for idx, course in enumerate(quarter['courses']):
                with cols[idx % 3]:
                    st.markdown(f"""
                        <div style="padding: 14px 16px; background: white; border-radius: 8px; border: 1px solid #d4e5db; margin-bottom: 10px;">
                            <div style="font-weight: 600; color: #2d5f3f; font-size: 14px;">{course['code']}</div>
                            <div style="font-size: 13px; color: #5a8169; margin-top: 4px;">{course['name']}</div>
                            <div style="font-size: 12px; color: #7ba88c; margin-top: 6px;">{course['credits']} credits</div>
                        </div>
                    """, unsafe_allow_html=True)
    
    # Summary
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
            <div style="padding: 20px; background: #f5faf7; border-radius: 12px;">
                <div style="font-size: 14px; color: #5a8169; margin-bottom: 4px;">Total Plan Credits</div>
                <div style="font-size: 24px; color: #2d5f3f; font-weight: 700;">
                    {st.session_state.generated_plan['total_credits']} credits
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state.completed_courses = []
            st.session_state.desired_courses = []
            st.session_state.completed_bulk_text = ""
            st.session_state.desired_bulk_text = ""
            st.session_state.generated_plan = None
            st.rerun()
        
        if st.button("📥 Export Plan", use_container_width=True):
            st.success("Export functionality would connect to your backend!")

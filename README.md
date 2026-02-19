# PIED PIPER - Course Planner

A beautiful, calming green-themed course planning application for undergraduate CS students.

## Features

- **Vertical Layout**: All sections visible from the start - no navigation required
- **Course Selection**: Select completed and desired courses with an intuitive interface
- **AI-Powered Planning**: Generate personalized quarter-by-quarter course plans
- **Calming Design**: Gentle green color scheme designed for students
- **Prerequisites Display**: See course prerequisites at a glance

## Installation

1. Make sure you have Python 3.8+ installed
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the App

Run the Streamlit app with:

```bash
streamlit run pied_piper_planner.py
```

The app will open in your browser at `http://localhost:8501`

## How to Use

1. **Select Completed Courses**: Check off all courses you've already taken
2. **Select Desired Courses**: Choose courses you want to take in the future
3. **Generate Plan**: Click the "Generate My Course Plan" button
4. **View Results**: Scroll down to see your personalized quarter-by-quarter plan
5. **Export or Start Over**: Export your plan or start fresh with new selections

## Customization

### Adding Courses

Edit the `COURSES_COMPLETED` and `COURSES_AVAILABLE` lists in `pied_piper_planner.py` to add your own courses:

```python
COURSES_COMPLETED = [
    {"code": "CS 101", "name": "Course Name", "credits": 3},
    # Add more courses...
]

COURSES_AVAILABLE = [
    {"code": "CS 202", "name": "Course Name", "credits": 4, "prereq": "CS 201"},
    # Add more courses...
]
```

### Connecting to Backend LLM

Replace the mock plan generation (around line 175) with your actual LLM API call:

```python
# Replace this section:
with st.spinner("Generating your personalized course plan..."):
    time.sleep(2)  # Remove this
    
    # Add your LLM API call here
    # response = your_llm_api_call(completed_courses, desired_courses)
    # st.session_state.generated_plan = parse_llm_response(response)
```

### Color Scheme

To change colors, edit the CSS in the `st.markdown()` section at the top of the file. Current green theme:
- Primary: `#4a8b5f`
- Dark: `#2d5f3f`
- Light: `#5a8169`
- Background: `#f0f9f4` to `#e8f5ed` gradient

## Project Structure

```
.
├── pied_piper_planner.py  # Main Streamlit application
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Notes

- The "Generate Plan" button is disabled until you select at least one completed and one desired course
- Course selections persist during your session
- The generated plan is a mock - connect your LLM backend for actual AI-powered planning
- Export functionality is a placeholder - implement your own export logic

## License

This is a course project. Use and modify as needed for your AI course assignment.

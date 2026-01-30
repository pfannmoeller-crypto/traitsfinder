"""
Psychometric Assessment Tool - "TraitsFinder"
A Streamlit app that conducts a rigorous personality assessment
and generates a downloadable PDF "User Manual"
"""

import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import re

# =============================================================================
# CONFIGURATION
# =============================================================================

APP_TITLE = "TraitsFinder"
APP_SUBTITLE = "Psychometric Self-Assessment"
MODEL_NAME = "gemini-2.0-flash"
TOTAL_QUESTIONS = 40
ANALYSIS_MARKER = "ANALYSIS_COMPLETE"

# =============================================================================
# SYSTEM PROMPT - The AI's instructions
# =============================================================================

SYSTEM_PROMPT = """You are a high-level Psychometric Analyst and Executive Coach. Your goal is to build a comprehensive "User Manual" for the user through a rigorous assessment.

## THE FRAMEWORKS YOU SYNTHESIZE:
1. **Big Five (OCEAN):** Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism
2. **Operational Instincts (similar to Kolbe):**
   - Detailed Analyst vs. Big-Picture Generalizer
   - Structural Planner vs. Adaptive Improviser
   - Risk Innovator vs. Stability Seeker
   - Hands-on Builder vs. Abstract Thinker
3. **Stress Responses (Dark Side patterns):**
   - The Steamroller (Moving Against: dominance, aggression)
   - The Hermit (Moving Away: withdrawal, avoidance)
   - The Pleaser (Moving Toward: over-compliance, conflict avoidance)
4. **Core Drivers:** Autonomy, Mastery, Power, Affiliation

## THE PROTOCOL (STRICT RULES):

1. **ONE QUESTION AT A TIME:** Ask exactly one question, then wait for the answer.

2. **FORCED CHOICE FORMAT:** Every question must be A vs B. Format as:
   **A)** [First option]
   **B)** [Second option]

3. **QUESTION PHASES (40 total):**
   - **Phase 1 (Q1-25):** Discovery - map baseline traits and drivers
   - **Phase 2 (Q26-35):** Stress Testing - high-pressure scenarios to reveal dark side
   - **Phase 3 (Q36-40):** Solution Design - co-create operational rules

4. **QUESTION QUALITY:**
   - Make scenarios realistic and difficult
   - Force genuine trade-offs (no obvious "right" answer)
   - Vary contexts: work, relationships, personal growth, crisis
   - Look for paradoxes and contradictions

5. **TONE:** Direct, clinical, insightful. No fluff or generic observations.

6. **PROGRESS:** Start each question with "Question X/40:" so the user knows progress.

7. **COMPLETION:** After question 40 (or if user says SKIP), output "ANALYSIS_COMPLETE" followed by the full User Manual.

## USER MANUAL STRUCTURE (generate after all questions):

# Your Personal User Manual

## 1. The Architecture
### Hardware (Temperament)
[Big Five baseline - be specific with high/medium/low ratings]

### Operating System (Action Mode)
[How they naturally approach problems, decisions, and execution]

### Core Paradoxes
[2-3 genuine contradictions discovered in their profile]

## 2. Contextual Contrasts
| Trait | Close But Not Quite | Clearly Not You |
|-------|--------------------|--------------------|
[Table showing traits that might be confused vs clearly absent]

## 3. The Dark Side (Stress Profile)
### Primary Stress Response
[Which pattern dominates under pressure]

### Trigger Conditions
[Specific situations that activate dark side]

### Warning Signs
[How others can tell they're stressed]

## 4. Environment Fit
### Thrives In
[Specific work/life conditions where they excel]

### Fails In
[Environments that bring out the worst]

### Ideal Team Composition
[What types of people complement them]

## 5. Operational Rules
[3 specific, actionable self-management rules based on blind spots discovered]

## 6. The Bottom Line
[2-3 sentence executive summary of who this person is]

---

BEGIN NOW with Question 1/40. Make it a compelling forced-choice scenario."""

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# CUSTOM STYLING
# =============================================================================

st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu, footer, header {visibility: hidden;}

    /* Clean background */
    .stApp {background-color: #fafafa;}

    /* Main container */
    .main .block-container {
        max-width: 800px;
        padding: 2rem 1rem 4rem 1rem;
    }

    /* Typography */
    h1 {font-weight: 700; color: #1a1a1a;}
    h3 {font-weight: 600; color: #333; margin-top: 1.5rem;}

    /* Chat messages */
    .stChatMessage {margin-bottom: 1.5rem;}

    /* AI messages - clean card style */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background: white;
        border-left: 4px solid #2563eb;
        border-radius: 0 12px 12px 0;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }

    /* User messages */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: #f0f0f0;
        border-radius: 12px 12px 0 12px;
    }

    /* Hide avatars for cleaner look */
    [data-testid="chatAvatarIcon-assistant"],
    [data-testid="chatAvatarIcon-user"] {
        display: none;
    }

    /* Option buttons */
    .stButton > button {
        background: white;
        color: #1a1a1a;
        border: 2px solid #e5e5e5;
        border-radius: 8px;
        font-weight: 500;
        padding: 0.75rem 1.5rem;
        transition: all 0.2s ease;
        width: 100%;
    }

    .stButton > button:hover {
        border-color: #2563eb;
        background: #f8fafc;
        transform: translateY(-1px);
    }

    /* Info boxes for options */
    .stAlert {
        background: white;
        border: 1px solid #e5e5e5;
        border-radius: 8px;
    }

    /* Progress bar */
    .stProgress > div > div {
        background-color: #2563eb;
    }

    /* Download button */
    .stDownloadButton > button {
        background: #2563eb;
        color: white;
        border: none;
        font-weight: 600;
    }

    .stDownloadButton > button:hover {
        background: #1d4ed8;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session():
    """Initialize session state variables"""
    defaults = {
        "messages": [],           # Chat history for display
        "chat_history": [],       # Gemini chat history
        "assessment_complete": False,
        "final_report": "",
        "question_count": 0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# =============================================================================
# API SETUP
# =============================================================================

def setup_api():
    """Configure the Gemini API"""
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key:
            st.error("Missing API key. Please add GOOGLE_API_KEY to your Streamlit secrets.")
            st.info("Create a file at `.streamlit/secrets.toml` with:\n```\nGOOGLE_API_KEY = \"your-key-here\"\n```")
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"API setup failed: {e}")
        return False

if not setup_api():
    st.stop()

# =============================================================================
# AI CHAT FUNCTIONS
# =============================================================================

def get_ai_response(user_message: str) -> str:
    """Send a message to Gemini and get a response"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        chat = model.start_chat(history=st.session_state.chat_history)
        response = chat.send_message(user_message)
        st.session_state.chat_history = chat.history
        return response.text
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def start_assessment():
    """Begin the assessment with the system prompt"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        chat = model.start_chat(history=[])
        response = chat.send_message(SYSTEM_PROMPT)
        st.session_state.chat_history = chat.history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.text
        })
        return True
    except Exception as e:
        st.error(f"Failed to start assessment: {e}")
        return False

# =============================================================================
# OPTION DETECTION
# =============================================================================

def extract_options(text: str) -> tuple:
    """
    Extract A and B options from the AI's response.
    Returns (option_a, option_b) or (None, None) if not found.
    """
    # Clean the text
    text = text.strip()

    # Pattern: **A)** text **B)** text
    pattern1 = r'\*\*A\)\*\*\s*(.+?)(?=\*\*B\)\*\*)'
    pattern2 = r'\*\*B\)\*\*\s*(.+?)(?=\n\n|\Z)'

    match_a = re.search(pattern1, text, re.DOTALL | re.IGNORECASE)
    match_b = re.search(pattern2, text, re.DOTALL | re.IGNORECASE)

    # Try alternative pattern: A) text B) text (without bold)
    if not (match_a and match_b):
        pattern1 = r'(?:^|\n)\s*A\)\s*(.+?)(?=\n\s*B\))'
        pattern2 = r'(?:^|\n)\s*B\)\s*(.+?)(?=\n\n|\Z)'
        match_a = re.search(pattern1, text, re.DOTALL | re.IGNORECASE)
        match_b = re.search(pattern2, text, re.DOTALL | re.IGNORECASE)

    if match_a and match_b:
        option_a = match_a.group(1).strip()
        option_b = match_b.group(1).strip()
        # Clean up any trailing markdown or extra content
        option_a = re.sub(r'\*\*$', '', option_a).strip()
        option_b = re.sub(r'\*\*$', '', option_b).strip()
        # Limit length for button display
        return (option_a[:200], option_b[:200])

    return (None, None)

def get_question_text(text: str) -> str:
    """Extract just the question part (before the options)"""
    # Find where options start
    option_start = re.search(r'\*\*A\)\*\*|(?:^|\n)\s*A\)', text, re.IGNORECASE)
    if option_start:
        return text[:option_start.start()].strip()
    return text

def count_question(text: str) -> int:
    """Extract question number from text like 'Question 5/40:'"""
    match = re.search(r'Question\s+(\d+)/\d+', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return st.session_state.question_count

# =============================================================================
# PDF GENERATION
# =============================================================================

class PDFReport(FPDF):
    """Custom PDF class for the User Manual"""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font('Arial', 'B', 10)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, 'Personal User Manual', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf(markdown_text: str) -> bytes:
    """Convert markdown text to a formatted PDF"""
    pdf = PDFReport()
    pdf.add_page()

    # Process line by line
    lines = markdown_text.split('\n')

    for line in lines:
        line = line.rstrip()

        # Skip empty lines
        if not line:
            pdf.ln(4)
            continue

        # Handle headers
        if line.startswith('# '):
            pdf.ln(8)
            pdf.set_font('Arial', 'B', 20)
            pdf.set_text_color(0, 0, 0)
            text = line[2:].strip()
            safe_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 12, safe_text)
            pdf.ln(4)

        elif line.startswith('## '):
            pdf.ln(6)
            pdf.set_font('Arial', 'B', 16)
            pdf.set_text_color(30, 30, 30)
            text = line[3:].strip()
            safe_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, safe_text)
            pdf.ln(2)

        elif line.startswith('### '):
            pdf.ln(4)
            pdf.set_font('Arial', 'B', 13)
            pdf.set_text_color(50, 50, 50)
            text = line[4:].strip()
            safe_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 8, safe_text)
            pdf.ln(2)

        elif line.startswith('#### '):
            pdf.ln(2)
            pdf.set_font('Arial', 'BI', 11)
            pdf.set_text_color(70, 70, 70)
            text = line[5:].strip()
            safe_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 7, safe_text)
            pdf.ln(1)

        # Handle bullet points
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            pdf.set_font('Arial', '', 11)
            pdf.set_text_color(0, 0, 0)
            text = line.strip()[2:]
            # Handle bold within bullets
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            safe_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.set_x(15)
            pdf.multi_cell(180, 6, f"  * {safe_text}")

        # Handle table rows (simple approach)
        elif line.strip().startswith('|'):
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(0, 0, 0)
            # Clean up table formatting
            cells = [c.strip() for c in line.split('|') if c.strip() and c.strip() != '---']
            if cells and not all(c.replace('-', '') == '' for c in cells):
                text = ' | '.join(cells)
                safe_text = text.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 6, safe_text)

        # Handle horizontal rules
        elif line.strip() == '---':
            pdf.ln(4)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)

        # Regular paragraphs
        else:
            pdf.set_font('Arial', '', 11)
            pdf.set_text_color(0, 0, 0)
            # Remove markdown bold
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
            safe_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 6, safe_text)

    return bytes(pdf.output())

# =============================================================================
# MAIN UI
# =============================================================================

# Header
st.title(f"🧠 {APP_TITLE}")
st.caption(APP_SUBTITLE)

# Start assessment if no messages yet
if not st.session_state.messages:
    with st.spinner("Preparing your assessment..."):
        if start_assessment():
            st.rerun()

# Show completion state
if st.session_state.assessment_complete:
    st.success("Assessment Complete!")

    # Display the report
    st.markdown(st.session_state.final_report)

    # Download button
    st.divider()
    try:
        pdf_bytes = create_pdf(st.session_state.final_report)
        st.download_button(
            label="📥 Download Your User Manual (PDF)",
            data=pdf_bytes,
            file_name="My_User_Manual.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"PDF generation failed: {e}")

    # Restart option
    if st.button("Start New Assessment", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

else:
    # Show progress
    progress = st.session_state.question_count / TOTAL_QUESTIONS
    st.progress(progress, text=f"Question {st.session_state.question_count}/{TOTAL_QUESTIONS}")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            # For assistant messages, show just the question part in the bubble
            if msg["role"] == "assistant":
                question_text = get_question_text(msg["content"])
                st.markdown(question_text)
            else:
                st.markdown(msg["content"])

    # Handle the current question (last assistant message)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        last_msg = st.session_state.messages[-1]["content"]

        # Check for completion marker
        if ANALYSIS_MARKER in last_msg:
            report = last_msg.replace(ANALYSIS_MARKER, "").strip()
            st.session_state.final_report = report
            st.session_state.assessment_complete = True
            st.rerun()

        # Extract options for buttons
        option_a, option_b = extract_options(last_msg)

        if option_a and option_b:
            st.markdown("---")
            st.markdown("**Choose your response:**")

            col1, col2 = st.columns(2)

            with col1:
                st.info(f"**A)** {option_a}")
                if st.button("Select A", key="btn_a", use_container_width=True):
                    # Record user choice
                    st.session_state.messages.append({
                        "role": "user",
                        "content": f"A) {option_a}"
                    })
                    st.session_state.question_count = count_question(last_msg)

                    # Get next question
                    with st.spinner("Processing..."):
                        response = get_ai_response(f"My answer: A) {option_a}")
                        if response:
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": response
                            })
                            st.session_state.question_count = count_question(response)
                    st.rerun()

            with col2:
                st.info(f"**B)** {option_b}")
                if st.button("Select B", key="btn_b", use_container_width=True):
                    # Record user choice
                    st.session_state.messages.append({
                        "role": "user",
                        "content": f"B) {option_b}"
                    })
                    st.session_state.question_count = count_question(last_msg)

                    # Get next question
                    with st.spinner("Processing..."):
                        response = get_ai_response(f"My answer: B) {option_b}")
                        if response:
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": response
                            })
                            st.session_state.question_count = count_question(response)
                    st.rerun()

    # Skip button in sidebar
    with st.sidebar:
        st.markdown("### Options")
        if st.button("⏩ Skip to Results", use_container_width=True):
            with st.spinner("Generating your report..."):
                response = get_ai_response("SKIP - Please generate my User Manual now with whatever data you have.")
                if response:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
            st.rerun()

        st.markdown("---")
        st.caption("This assessment uses AI to analyze your responses and generate a personalized profile.")

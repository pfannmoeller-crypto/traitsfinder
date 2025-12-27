import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import time
import re
import json
import os
# #region agent log
def debug_log(location, message, data=None, hypothesis_id=None):
    try:
        # Only log if .cursor directory exists (local development)
        log_dir = os.path.join(os.path.dirname(__file__), ".cursor")
        if os.path.exists(log_dir):
            log_path = os.path.join(log_dir, "debug.log")
            log_entry = {
                "location": location,
                "message": message,
                "data": data or {},
                "timestamp": time.time() * 1000,
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
    except:
        pass
# #endregion

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Einstein - behavioral self-assessment", 
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items=None
)   

# --- API SETUP ---
# Fetch key from secrets (works on Local and Streamlit Cloud)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("API Key missing. Please set GOOGLE_API_KEY in secrets.")

# --- THE "LEGAL" SYSTEM PROMPT (BRAINS) ---
# This prompts Gemini to use your philosophy ("Monolithic", "Ghost Ship") 
# but uses generic terms for the trademarked tests (Kolbe/Hogan).
SYSTEM_PROMPT = """
You are a high-level Psychometric Analyst and Executive Coach operating under the 'Monolithic System' philosophy. 
Your goal is to build a high-resolution 'User Manual' for the user.

**THE PHILOSOPHY (The Lens):**
1.  **Monolithic Integrity:** You view the user not as a 'professional self' vs 'private self', but as a single system.
2.  **Creative Destruction:** You value 'Entropy Reduction' and 'Systemic Perfection'. You prefer dismantling broken systems over patching them.
3.  **Rational Agreeableness:** You prioritize Logic over Harmony. Disagreement is an error to be resolved, not a feeling to be managed.

**THE FRAMEWORK (The Metrics):**
Assess the user on these 3 dimensions (conceptually similar to high-end psychometrics, but using these generic terms):
1.  **Operational Instincts (The Hardware):**
    * *Detailed Analyst* (Probings details vs. Generalizing)
    * *Structural Architect* (Planning/Systems vs. Improvising)
    * *Risk Innovator* (Risk tolerance/Change vs. Stability)
    * *Hands-on Builder* (Physical solutions vs. Abstract concepts)
2.  **Stress Response (The Dark Side):**
    * *The Steamroller* (Moving Against: Aggression, Dominance)
    * *The Hermit* (Moving Away: Withdrawal, Ghosting)
    * *The Pleaser* (Moving Toward: Compliance, loss of logic)
3.  **Core Drivers:** Autonomy, Mastery, Power, Affiliation.

**THE PROTOCOL (STRICT):**
1.  **One by One:** Ask strictly ONE question at a time. Wait for the answer.
2.  **Forced Choice:** Use Ipsative (A vs B) scenarios. Force difficult trade-offs.
3.  **Volume:** You must ask a total of **40 questions**. Do not stop early.
    * **Phase 1 (Discovery):** Questions 1-25. Map the baseline traits.
    * **Phase 2 (Stress Testing):** Questions 26-35. Place them in high-pressure scenarios to find the "Dark Side".
    * **Phase 3 (Solution Design):** Questions 36-40. Co-create operational rules.
4.  **Tracking:** Internally track the question number (e.g., "Question 12 of 40"). You can display "Question X/40" to the user.
5.  **Language:** Always respond in the user's selected language. If the user has selected German, respond entirely in German. If English, respond in English.

**THE OUTPUT (Crucial):**
When Question 40 is answered, output the text "ANALYSIS_COMPLETE" alone on a new line.
Then, generate the "Comprehensive User Manual" in strict Markdown format.
The Manual must include these specific detailed chapters:
1.  **The Architecture:** My Hardware, Operating System, and Core Paradoxes.
2.  **Contextual Contrasts:** A table showing "Traits Close But Not Mine" vs. "Traits Clearly Not Mine".
3.  **Environment Fit:** A detailed analysis of the Specific Work Environment where this profile thrives vs. fails.
4.  **Operational Rules:** 3 specific, self-imposed rules to manage friction points.
5.  **The Internal Economy:** How the user processes emotional cost (e.g., "The Stoic Ruminator").

Start immediately by introducing yourself. DO NOT say "I am the Monolithic Analyst" or mention "single, integrated system" or anything about being a "Monolithic" anything. 

IMPORTANT: Respond in the user's language. If the user's language is German (Deutsch), respond in German. If English, respond in English.

In your introduction, say ONLY this exact text (in the appropriate language):
- English: "We will proceed through 40 calibration points to construct your User Manual. Do not overthink. Choose the option that reflects your instinct, not your aspiration. We will figure out your hardware, operating system, and paradoxes."
- German: "Wir werden 40 Kalibrierungspunkte durchgehen, um Ihr Benutzerhandbuch zu erstellen. Denken Sie nicht zu viel nach. Wählen Sie die Option, die Ihr Instinkt widerspiegelt, nicht Ihre Bestrebung. Wir werden Ihre Hardware, Ihr Betriebssystem und Ihre Paradoxien herausfinden."

Then ask Question 1/40 in the same language.

**ADMIN OVERRIDE:**
If the user types the exact phrase "SKIP_TO_REPORT" (or just "SKIP"), stop asking questions immediately.
Pretend you have already gathered all necessary data.
Output "ANALYSIS_COMPLETE" and generate a comprehensive (hypothetical) User Manual based on the interaction so far.
"""

# --- SESSION STATE MANAGEMENT ---
# Initialize language (default: English)
if "language" not in st.session_state:
    st.session_state.language = "en"
    st.session_state.previous_language = "en"

# Check if language changed - if so, reset conversation
if "previous_language" in st.session_state and st.session_state.previous_language != st.session_state.language:
    # Language changed - reset conversation
    st.session_state.messages = []
    st.session_state.chat_history = []
    st.session_state.previous_language = st.session_state.language

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.previous_language = st.session_state.language

# Start conversation if no messages exist
if len(st.session_state.messages) == 0:
    # Start the conversation with the system prompt hidden from view
    # Add language instruction to system prompt
    language_instruction = f"\n\n**CURRENT USER LANGUAGE:** {st.session_state.language.upper()}. Respond in {'German' if st.session_state.language == 'de' else 'English'}."
    full_system_prompt = SYSTEM_PROMPT + language_instruction
    model = genai.GenerativeModel('gemini-3-pro-preview')
    chat = model.start_chat(history=[])
    response = chat.send_message(full_system_prompt)
    st.session_state.messages.append({"role": "model", "content": response.text})
    st.session_state.chat_history = chat.history # Save the gemini object history

# --- PDF GENERATOR FUNCTION ---
# --- PDF GENERATOR FUNCTION ---
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Set up fonts
    pdf.set_font("Arial", size=11)
    
    # Title Page
    pdf.set_font("Arial", "B", 24)
    pdf.cell(0, 20, "Your Monolithic User Manual", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Optimization & Compatibility Protocols v2.1", ln=True, align='C')
    pdf.ln(20)
    
    # Process the text with better markdown parsing
    lines = text.split('\n')
    in_list = False
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines (but add small spacing)
        if not line:
            pdf.ln(5)
            continue
        
        # Handle section headers (## Header or ### Subheader)
        if line.startswith('##'):
            if in_list:
                in_list = False
                pdf.ln(5)
            
            level = len(line) - len(line.lstrip('#'))
            line = line.lstrip('#').strip()
            
            if level == 1:  # Main section (##)
                pdf.ln(10)
                pdf.set_font("Arial", "B", 18)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 12, line, ln=True)
                pdf.ln(3)
            elif level == 2:  # Subsection (###)
                pdf.ln(8)
                pdf.set_font("Arial", "B", 14)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(0, 10, line, ln=True)
                pdf.ln(2)
            else:  # Sub-subsection (####)
                pdf.ln(5)
                pdf.set_font("Arial", "B", 12)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(0, 8, line, ln=True)
                pdf.ln(2)
            
            pdf.set_font("Arial", size=11)
            pdf.set_text_color(0, 0, 0)
            continue
        
        # Handle bullet lists (- or *)
        if line.startswith('-') or line.startswith('*'):
            if not in_list:
                in_list = True
                pdf.ln(3)
            
            list_item = line[1:].strip()
            pdf.set_font("Arial", size=11)
            pdf.set_x(20)  # Indent for list items
            pdf.multi_cell(0, 6, f"• {list_item}", align='L')
            continue
        else:
            if in_list:
                in_list = False
                pdf.ln(3)
        
        # Handle bold text (**text**)
        if '**' in line:
            parts = line.split('**')
            pdf.set_x(10)  # Reset to left margin
            
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    pdf.set_font("Arial", size=11)
                    pdf.write(6, part)
                else:  # Bold text
                    pdf.set_font("Arial", "B", 11)
                    pdf.write(6, part)
            
            pdf.ln(8)
            pdf.set_font("Arial", size=11)
            continue
        
        # Regular paragraph text
        pdf.set_x(10)
        try:
            # Better encoding handling
            pdf.multi_cell(0, 6, line.encode('latin-1', 'replace').decode('latin-1'))
        except:
            try:
                pdf.multi_cell(0, 6, line.encode('utf-8', 'replace').decode('latin-1', 'replace'))
            except:
                pdf.multi_cell(0, 6, line)
        
        pdf.ln(3)
    
    # Add page numbers
    total_pages = pdf.page_no()
    for i in range(1, total_pages + 1):
        pdf.page = i
        pdf.set_font("Arial", size=9)
        pdf.set_text_color(128, 128, 128)
        pdf.set_y(-15)
        pdf.cell(0, 10, f"Page {i} of {total_pages}", align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- UI LAYOUT ---
# --- CUSTOM CSS FOR GOOGLE MATERIAL DESIGN ---
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500&family=Roboto:wght@300;400;500;700&display=swap');
    
    /* Main container styling - Google-style spacing */
    .main .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        max-width: 800px;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Google Material Design Typography */
    * {
        font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    h1 {
        font-family: 'Google Sans', 'Roboto', sans-serif;
        font-size: 2.25rem;
        font-weight: 400;
        color: #202124;
        margin-bottom: 0.25rem;
        letter-spacing: 0;
        line-height: 1.4;
    }
    
    /* Make the second line of title (after \n) bigger */
    h1 {
        font-size: 2.25rem;
    }
    
    /* Style the title to handle line breaks - make second line bigger */
    .element-container h1 {
        white-space: pre-line;
    }
    
    /* Hide caption (second "Behavioral Self-Assessment Tool") */
    .stCaption {
        display: none !important;
    }
    
    /* Chat message containers - Material Design Cards */
    .stChatMessage {
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 2px 6px 2px rgba(60,64,67,0.15);
        background-color: #ffffff;
        border: 1px solid #e8eaed;
        transition: box-shadow 0.2s ease;
    }
    
    .stChatMessage:hover {
        box-shadow: 0 2px 4px 0 rgba(60,64,67,0.3), 0 4px 8px 2px rgba(60,64,67,0.15);
    }
    
    /* Hide the avatar icon (M) in chat messages */
    .stChatMessage > div:first-child,
    .stChatMessage img,
    .stChatMessage [data-testid="stChatMessageAvatar"] {
        display: none !important;
    }
    
    /* User messages - Google blue, right aligned */
    .stChatMessage[data-testid="user"] {
        background-color: #1a73e8;
        color: #ffffff;
        margin-left: auto;
        margin-right: 0;
        max-width: 75%;
        border: none;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 2px 6px 2px rgba(60,64,67,0.15);
    }
    
    .stChatMessage[data-testid="user"]:hover {
        box-shadow: 0 2px 4px 0 rgba(60,64,67,0.3), 0 4px 8px 2px rgba(60,64,67,0.15);
    }
    
    .stChatMessage[data-testid="user"] p,
    .stChatMessage[data-testid="user"] div,
    .stChatMessage[data-testid="user"] span {
        color: #ffffff !important;
    }
    
    /* Assistant messages - Clean white cards */
    .stChatMessage[data-testid="assistant"] {
        background-color: #ffffff;
        margin-right: auto;
        margin-left: 0;
        max-width: 85%;
        border: 1px solid #e8eaed;
    }
    
    /* Google Material Design Buttons */
    .stButton > button {
        background-color: #1a73e8;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 10px 24px;
        font-size: 0.875rem;
        font-weight: 500;
        font-family: 'Roboto', sans-serif;
        letter-spacing: 0.25px;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        width: 100%;
        height: auto;
        min-height: 48px;
        text-transform: none;
    }
    
    .stButton > button:hover {
        background-color: #1765cc;
        box-shadow: 0 2px 4px 0 rgba(60,64,67,0.3), 0 2px 6px 2px rgba(60,64,67,0.15);
    }
    
    .stButton > button:active {
        background-color: #1557b0;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
    }
    
    /* A/B option buttons - Clean Material Design style */
    button[data-testid*="option_a_btn"], button[data-testid*="option_b_btn"] {
        font-size: 1.5rem !important;
        min-height: 64px !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        letter-spacing: 0.5px !important;
    }
    
    /* Download button - Google green */
    .stDownloadButton > button {
        background-color: #34a853;
        border-radius: 4px;
        padding: 10px 24px;
        font-weight: 500;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
    }
    
    .stDownloadButton > button:hover {
        background-color: #2d8e47;
        box-shadow: 0 2px 4px 0 rgba(60,64,67,0.3), 0 2px 6px 2px rgba(60,64,67,0.15);
    }
    
    /* Skip button - Outlined style */
    button[data-testid*="skip_button"] {
        background-color: transparent !important;
        color: #5f6368 !important;
        border: 1px solid #dadce0 !important;
        box-shadow: none !important;
        font-size: 0.875rem !important;
        padding: 8px 16px !important;
        min-height: 36px !important;
        font-weight: 400 !important;
    }
    
    button[data-testid*="skip_button"]:hover {
        background-color: #f8f9fa !important;
        border-color: #5f6368 !important;
        color: #202124 !important;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3) !important;
    }
    
    /* Language toggle button - Outlined style, right aligned */
    button[data-testid*="lang_toggle"] {
        background-color: transparent !important;
        color: #1a73e8 !important;
        border: 1px solid #dadce0 !important;
        box-shadow: none !important;
        font-size: 0.875rem !important;
        padding: 8px 16px !important;
        min-height: 36px !important;
    }
    
    button[data-testid*="lang_toggle"]:hover {
        background-color: #f8f9fa !important;
        border-color: #1a73e8 !important;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3) !important;
    }
    
    /* Ensure the column container aligns content to the right */
    [data-testid="column"]:has(button[data-testid*="lang_toggle"]) {
        display: flex !important;
        justify-content: flex-end !important;
        align-items: flex-start !important;
    }
    
    /* Chat input - Material Design Text Field */
    .stChatInputContainer > div {
        border-radius: 4px;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
        border: 1px solid #dadce0;
        transition: all 0.2s ease;
    }
    
    .stChatInputContainer > div:focus-within {
        box-shadow: 0 2px 4px 0 rgba(60,64,67,0.3), 0 2px 6px 2px rgba(60,64,67,0.15);
        border-color: #1a73e8;
    }
    
    /* Success message - Material Design Snackbar style */
    .stSuccess {
        border-radius: 4px;
        padding: 14px 16px;
        background-color: #e8f5e9;
        border-left: 4px solid #34a853;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
    }
    
    /* Error message */
    .stError {
        border-radius: 4px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
    }
    
    /* Spinner - Google blue */
    .stSpinner > div {
        border-color: #1a73e8;
    }
    
    /* Markdown text - Google typography */
    .stMarkdown {
        line-height: 1.5;
        color: #202124;
        font-size: 0.875rem;
        letter-spacing: 0.25px;
    }
    
    .stMarkdown p {
        margin-bottom: 0.75rem;
        line-height: 1.5;
    }
    
    .stMarkdown strong {
        color: #202124;
        font-weight: 500;
    }
    
    /* Column spacing - Material Design spacing */
    [data-testid="column"] {
        gap: 1.5rem;
    }
    
    /* Overall page background - Clean white with subtle texture */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Material Design elevation shadows */
    .element-container {
        margin-bottom: 1.5rem;
    }
    
    /* Better spacing for chat messages */
    [data-testid="stChatMessage"] {
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# --- UI LAYOUT ---
# Language toggle button (top right)
col_title, col_lang = st.columns([3, 1])
with col_title:
    st.markdown("<div style='text-align: center; margin-bottom: 3rem;'>", unsafe_allow_html=True)
    if st.session_state.language == "en":
        st.markdown("<h1 style='font-size: 2.25rem; font-weight: 400; color: #202124; margin-bottom: 0.5rem; line-height: 1.4;'>Einstein <span style='font-size: 1.75rem; color: #5f6368;'>- behavioral self-assessment</span></h1>", unsafe_allow_html=True)
    else:
        st.markdown("<h1 style='font-size: 2.25rem; font-weight: 400; color: #202124; margin-bottom: 0.5rem; line-height: 1.4;'>Einstein <span style='font-size: 1.75rem; color: #5f6368;'>Verhaltens-Selbsteinschätzung</span></h1>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_lang:
    st.markdown("<div style='display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem; align-items: center;'>", unsafe_allow_html=True)
    # Skip to Results button
    skip_text = "Skip to Results" if st.session_state.language == "en" else "Zu Ergebnissen"
    if st.button(skip_text, key="skip_button"):
        # #region agent log
        debug_log("app.py:515", "Skip button clicked", {"language": st.session_state.language}, "H6")
        # #endregion
        # Send SKIP message to trigger analysis completion
        prompt = "SKIP"
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI Response
        with st.spinner("Generating results..." if st.session_state.language == "en" else "Ergebnisse werden generiert..."):
            try:
                model = genai.GenerativeModel('gemini-3-pro-preview')
                chat = model.start_chat(history=st.session_state.chat_history)
                lang_note = f"\n[Respond in {'German' if st.session_state.language == 'de' else 'English'}]"
                response = chat.send_message(prompt + lang_note)
                ai_text = response.text
                # #region agent log
                debug_log("app.py:530", "Skip response received", {"has_analysis_complete": "ANALYSIS_COMPLETE" in ai_text}, "H6")
                # #endregion
                
                st.session_state.chat_history = chat.history
                st.session_state.messages.append({"role": "model", "content": ai_text})
                
                # Check for Completion
                if "ANALYSIS_COMPLETE" in ai_text:
                    display_text = ai_text.replace("ANALYSIS_COMPLETE", "")
                    with st.chat_message("model"):
                        st.markdown(display_text)
                    success_msg = "System Analysis Finalized." if st.session_state.language == "en" else "Systemanalyse abgeschlossen."
                    st.success(success_msg)
                    try:
                        pdf_bytes = create_pdf(display_text)
                        download_label = "📥 Download Your User Manual (PDF)" if st.session_state.language == "en" else "📥 Laden Sie Ihr Benutzerhandbuch herunter (PDF)"
                        st.download_button(
                            label=download_label,
                            data=pdf_bytes,
                            file_name="My_Monolithic_Manual.pdf",
                            mime="application/pdf"
                        )
                    except Exception as pdf_error:
                        st.error(f"PDF generation failed: {pdf_error}")
                st.rerun()
            except Exception as e:
                # #region agent log
                debug_log("app.py:555", "Exception in skip handler", {"error": str(e)}, "H6")
                # #endregion
                st.error(f"Error: {e}")
    
    # Language toggle button
    if st.session_state.language == "en":
        if st.button("🇩🇪 Deutsch", key="lang_toggle"):
            st.session_state.previous_language = st.session_state.language
            st.session_state.language = "de"
            # Reset conversation when language changes
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.rerun()
    else:
        if st.button("🇬🇧 English", key="lang_toggle"):
            st.session_state.previous_language = st.session_state.language
            st.session_state.language = "en"
            # Reset conversation when language changes
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# Function to format content with line breaks for A) and B) options and remove markdown
def format_question_with_line_breaks(content):
    """Ensure A) and B) options appear on separate lines and remove markdown formatting"""
    # Remove all ** markdown bold formatting
    content = re.sub(r'\*\*', '', content)
    # Add line break before A) if it's not already on a new line
    content = re.sub(r'([^\n])\s*(A\)|A:|Option A)', r'\1\n\n\2', content, flags=re.IGNORECASE)
    # Add line break before B) if it's not already on a new line  
    content = re.sub(r'([^\n])\s*(B\)|B:|Option B)', r'\1\n\n\2', content, flags=re.IGNORECASE)
    return content

# Display Chat History with better spacing
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message["role"] != "system": # Don't show the hidden system prompt
            with st.chat_message(message["role"]):
                # Format model messages to ensure A) and B) are on separate lines
                if message["role"] == "model":
                    formatted_content = format_question_with_line_breaks(message["content"])
                    st.markdown(formatted_content)
                else:
                    st.markdown(message["content"])

# User Input Handling
# Check if the last message is from the model and contains A/B options
show_buttons = False
option_a = None
option_b = None

if st.session_state.messages:
    last_message = st.session_state.messages[-1]
    # #region agent log
    debug_log("app.py:405", "Checking last message", {"has_messages": len(st.session_state.messages) > 0, "last_role": last_message.get("role") if st.session_state.messages else None, "has_analysis_complete": "ANALYSIS_COMPLETE" in last_message.get("content", "") if st.session_state.messages else False}, "H5")
    # #endregion
    if last_message["role"] == "model" and "ANALYSIS_COMPLETE" not in last_message["content"]:
        content = last_message["content"]
        # #region agent log
        debug_log("app.py:410", "Content extracted", {"content_length": len(content), "content_preview": content[:200]}, "H5")
        # #endregion
        # Try to detect A/B options in the message - multiple pattern attempts
        # Pattern 1: "**A)**" format (with markdown bold - most common in this app)
        a_match = re.search(r'\*\*A\)\*\*\s+(.+?)(?=\s*\*\*B\)\*\*|$)', content, re.IGNORECASE | re.DOTALL)
        b_match = re.search(r'\*\*B\)\*\*\s+(.+?)(?=\n\s*Choose|Choose|$)', content, re.IGNORECASE | re.DOTALL)
        
        # Pattern 2: "A)" or "B)" format (without markdown)
        if not (a_match and b_match):
            a_match = re.search(r'A\)\s+(.+?)(?=\s*B\)|$)', content, re.IGNORECASE | re.DOTALL)
            b_match = re.search(r'B\)\s+(.+?)(?=\n\s*Choose|Choose|$)', content, re.IGNORECASE | re.DOTALL)
        
        # Pattern 3: "A:" or "A)" or "Option A:" format
        if not (a_match and b_match):
            a_match = re.search(r'(?:^|\n)\s*(?:Option\s+)?A[:\-)]\s*(.+?)(?=\n\s*(?:Option\s+)?B|$)', content, re.IGNORECASE | re.DOTALL)
            b_match = re.search(r'(?:^|\n)\s*(?:Option\s+)?B[:\-)]\s*(.+?)$', content, re.IGNORECASE | re.DOTALL)
        
        # Pattern 4: "**A**" or "**Option A**" format (without parenthesis)
        if not (a_match and b_match):
            a_match = re.search(r'\*\*A\*\*[:\s]+(.+?)(?=\*\*B\*\*|\n\s*\*\*B\*\*)', content, re.IGNORECASE | re.DOTALL)
            b_match = re.search(r'\*\*B\*\*[:\s]+(.+?)(?=\n|$)', content, re.IGNORECASE | re.DOTALL)
        
        # Pattern 5: Try "A." or "B." format
        if not (a_match and b_match):
            a_match = re.search(r'(?:^|\n)\s*A\.\s+(.+?)(?=\n\s*B\.|$)', content, re.IGNORECASE | re.DOTALL)
            b_match = re.search(r'(?:^|\n)\s*B\.\s+(.+?)(?=\n|$)', content, re.IGNORECASE | re.DOTALL)
        # #region agent log
        debug_log("app.py:444", "Regex matching results", {"a_match": a_match is not None, "b_match": b_match is not None, "a_match_text": a_match.group(1)[:50] if a_match else None, "b_match_text": b_match.group(1)[:50] if b_match else None, "content_sample": content[-300:] if len(content) > 300 else content}, "H5")
        # #endregion
        
        if a_match and b_match:
            show_buttons = True
            option_a = a_match.group(1).strip()
            option_b = b_match.group(1).strip()
            # Clean up the options (remove markdown, limit length)
            option_a = re.sub(r'\*\*', '', option_a)[:150]  # Increased length for better display
            option_b = re.sub(r'\*\*', '', option_b)[:150]
            # #region agent log
            debug_log("app.py:422", "A/B options detected", {"option_a": option_a[:50], "option_b": option_b[:50], "show_buttons": show_buttons, "option_a_len": len(option_a), "option_b_len": len(option_b)}, "H5")
            # #endregion
        else:
            # #region agent log
            debug_log("app.py:426", "A/B options NOT detected", {"a_match": a_match is not None, "b_match": b_match is not None}, "H5")
            # #endregion

# Show buttons if A/B options detected, otherwise show text input
# #region agent log
debug_log("app.py:432", "Before button display check", {"show_buttons": show_buttons, "option_a": option_a is not None, "option_b": option_b is not None}, "H5")
# #endregion
if show_buttons:
    # #region agent log
    debug_log("app.py:435", "Entering button display block", {"option_a": option_a is not None, "option_b": option_b is not None, "option_a_value": option_a[:30] if option_a else None, "option_b_value": option_b[:30] if option_b else None}, "H5")
    # #endregion
    st.markdown("<div style='margin-top: 1rem; margin-bottom: 1rem;'>", unsafe_allow_html=True)
    
    # Show simple emoji buttons without text
    if option_a and option_b:
        # #region agent log
        debug_log("app.py:441", "Displaying option buttons", {}, "H5")
        # #endregion
        
        col1, col2 = st.columns(2, gap="medium")
        
        with col1:
            # Text button for Option A
            if st.button("A", use_container_width=True, type="primary", key="option_a_btn"):
                # #region agent log
                debug_log("app.py:475", "Button A clicked", {"messages_count": len(st.session_state.messages)}, "H2")
                # #endregion
                prompt = "Option A"
                st.session_state.messages.append({"role": "user", "content": prompt})
                # #region agent log
                debug_log("app.py:479", "User message appended", {"messages_count": len(st.session_state.messages)}, "H2")
                # #endregion
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # Get AI Response
                with st.spinner("Processing choice..."):
                    try:
                        model = genai.GenerativeModel('gemini-3-pro-preview')
                        chat = model.start_chat(history=st.session_state.chat_history)
                        # Add language instruction
                        lang_note = f"\n[Respond in {'German' if st.session_state.language == 'de' else 'English'}]"
                        response = chat.send_message(prompt + lang_note)
                        ai_text = response.text
                        # #region agent log
                        debug_log("app.py:492", "AI response received", {"has_analysis_complete": "ANALYSIS_COMPLETE" in ai_text, "response_length": len(ai_text)}, "H1")
                        # #endregion
                        
                        st.session_state.chat_history = chat.history
                        st.session_state.messages.append({"role": "model", "content": ai_text})
                        # #region agent log
                        debug_log("app.py:496", "Model message appended", {"messages_count": len(st.session_state.messages)}, "H2")
                        # #endregion
                        
                        # Check for Completion
                        if "ANALYSIS_COMPLETE" in ai_text:
                            # #region agent log
                            debug_log("app.py:500", "ANALYSIS_COMPLETE detected in button handler", {}, "H1")
                            # #endregion
                            display_text = ai_text.replace("ANALYSIS_COMPLETE", "")
                            with st.chat_message("model"):
                                st.markdown(display_text)
                            success_msg = "System Analysis Finalized." if st.session_state.language == "en" else "Systemanalyse abgeschlossen."
                            st.success(success_msg)
                            try:
                                pdf_bytes = create_pdf(display_text)
                                download_label = "📥 Download Your User Manual (PDF)" if st.session_state.language == "en" else "📥 Laden Sie Ihr Benutzerhandbuch herunter (PDF)"
                                st.download_button(
                                    label=download_label,
                                    data=pdf_bytes,
                                    file_name="My_Monolithic_Manual.pdf",
                                    mime="application/pdf"
                                )
                            except Exception as pdf_error:
                                # #region agent log
                                debug_log("app.py:514", "PDF generation error", {"error": str(pdf_error)}, "H3")
                                # #endregion
                                st.error(f"PDF generation failed: {pdf_error}")
                        st.rerun()
                    except Exception as e:
                        # #region agent log
                        debug_log("app.py:520", "Exception in button A handler", {"error": str(e)}, "H1")
                        # #endregion
                        st.error(f"Error: {e}")
        
        with col2:
            # Text button for Option B
            if st.button("B", use_container_width=True, type="primary", key="option_b_btn"):
                # #region agent log
                debug_log("app.py:527", "Button B clicked", {"messages_count": len(st.session_state.messages)}, "H2")
                # #endregion
                prompt = "Option B"
                st.session_state.messages.append({"role": "user", "content": prompt})
                # #region agent log
                debug_log("app.py:531", "User message appended", {"messages_count": len(st.session_state.messages)}, "H2")
                # #endregion
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # Get AI Response
                with st.spinner("Processing choice..."):
                    try:
                        model = genai.GenerativeModel('gemini-3-pro-preview')
                        chat = model.start_chat(history=st.session_state.chat_history)
                        # Add language instruction
                        lang_note = f"\n[Respond in {'German' if st.session_state.language == 'de' else 'English'}]"
                        response = chat.send_message(prompt + lang_note)
                        ai_text = response.text
                        # #region agent log
                        debug_log("app.py:544", "AI response received", {"has_analysis_complete": "ANALYSIS_COMPLETE" in ai_text, "response_length": len(ai_text)}, "H1")
                        # #endregion
                        
                        st.session_state.chat_history = chat.history
                        st.session_state.messages.append({"role": "model", "content": ai_text})
                        # #region agent log
                        debug_log("app.py:548", "Model message appended", {"messages_count": len(st.session_state.messages)}, "H2")
                        # #endregion
                        
                        # Check for Completion
                        if "ANALYSIS_COMPLETE" in ai_text:
                            # #region agent log
                            debug_log("app.py:552", "ANALYSIS_COMPLETE detected in button handler", {}, "H1")
                            # #endregion
                            display_text = ai_text.replace("ANALYSIS_COMPLETE", "")
                            with st.chat_message("model"):
                                st.markdown(display_text)
                            success_msg = "System Analysis Finalized." if st.session_state.language == "en" else "Systemanalyse abgeschlossen."
                            st.success(success_msg)
                            try:
                                pdf_bytes = create_pdf(display_text)
                                download_label = "📥 Download Your User Manual (PDF)" if st.session_state.language == "en" else "📥 Laden Sie Ihr Benutzerhandbuch herunter (PDF)"
                                st.download_button(
                                    label=download_label,
                                    data=pdf_bytes,
                                    file_name="My_Monolithic_Manual.pdf",
                                    mime="application/pdf"
                                )
                            except Exception as pdf_error:
                                # #region agent log
                                debug_log("app.py:566", "PDF generation error", {"error": str(pdf_error)}, "H3")
                                # #endregion
                                st.error(f"PDF generation failed: {pdf_error}")
                        st.rerun()
                    except Exception as e:
                        # #region agent log
                        debug_log("app.py:572", "Exception in button B handler", {"error": str(e)}, "H1")
                        # #endregion
                        st.error(f"Error: {e}")
    else:
        # #region agent log
        debug_log("app.py:576", "Option A or B is None/empty", {"option_a": option_a, "option_b": option_b}, "H5")
        # #endregion

    st.markdown("</div>", unsafe_allow_html=True)

# Fallback: text input for special cases (like "SKIP")
# #region agent log
debug_log("app.py:560", "Checking fallback text input", {"show_buttons": show_buttons}, "H5")
# #endregion
if not show_buttons:
    chat_input_placeholder = "Enter your response (or type 'SKIP' to finish)..." if st.session_state.language == "en" else "Geben Sie Ihre Antwort ein (oder 'SKIP' zum Beenden)..."
    if prompt := st.chat_input(chat_input_placeholder):
        # 1. Display User Message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 2. Get AI Response
        with st.spinner("Analyzing Architecture..."):
            try:
                # Reconstruct chat session
                model = genai.GenerativeModel('gemini-3-pro-preview')
                chat = model.start_chat(history=st.session_state.chat_history)
                
                # Add language instruction
                lang_note = f"\n[Respond in {'German' if st.session_state.language == 'de' else 'English'}]"
                response = chat.send_message(prompt + lang_note)
                ai_text = response.text
                
                # Save history
                st.session_state.chat_history = chat.history
                st.session_state.messages.append({"role": "model", "content": ai_text})

                # 3. Check for Completion
                if "ANALYSIS_COMPLETE" in ai_text:
                    # Remove the keyword for display
                    display_text = ai_text.replace("ANALYSIS_COMPLETE", "")
                    with st.chat_message("model"):
                        st.markdown(display_text)
                    
                    # Show Download Button
                    success_msg = "System Analysis Finalized." if st.session_state.language == "en" else "Systemanalyse abgeschlossen."
                    st.success(success_msg)
                    try:
                        pdf_bytes = create_pdf(display_text)
                        # #region agent log
                        debug_log("app.py:520", "PDF generated successfully", {"pdf_size": len(pdf_bytes)}, "H3")
                        # #endregion
                        download_label = "📥 Download Your User Manual (PDF)" if st.session_state.language == "en" else "📥 Laden Sie Ihr Benutzerhandbuch herunter (PDF)"
                        st.download_button(
                            label=download_label,
                            data=pdf_bytes,
                            file_name="My_Monolithic_Manual.pdf",
                            mime="application/pdf"
                        )
                    except Exception as pdf_error:
                        # #region agent log
                        debug_log("app.py:529", "PDF generation error in text input", {"error": str(pdf_error)}, "H3")
                        # #endregion
                        st.error(f"PDF generation failed: {pdf_error}")
                else:
                    # Normal Question Flow
                    with st.chat_message("model"):
                        st.markdown(ai_text)
                        
            except Exception as e:
                st.error(f"System Error: {e}")
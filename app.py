import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import time
import re
import json
import os

# --- CONSTANTS ---
ANALYSIS_COMPLETE_MARKER = "ANALYSIS_COMPLETE"
MODEL_NAME = "gemini-3-pro-preview"
PDF_FILENAME = "My_Monolithic_Manual.pdf"

# Language strings
LANG_TEXTS = {
    "en": {
        "skip": "Skip to Results",
        "generating": "Generating results...",
        "processing": "Processing choice...",
        "analyzing": "Analyzing Architecture...",
        "finalized": "System Analysis Finalized.",
        "download": "📥 Download Your User Manual (PDF)",
        "chat_placeholder": "Enter your response (or type 'SKIP' to finish)...",
        "error_pdf": "PDF generation failed: {error}",
        "error_system": "System Error: {error}",
        "error_api_key": "API Key missing. Please set GOOGLE_API_KEY in secrets."
    },
    "de": {
        "skip": "Zu Ergebnissen",
        "generating": "Ergebnisse werden generiert...",
        "processing": "Auswahl wird verarbeitet...",
        "analyzing": "Architektur wird analysiert...",
        "finalized": "Systemanalyse abgeschlossen.",
        "download": "📥 Laden Sie Ihr Benutzerhandbuch herunter (PDF)",
        "chat_placeholder": "Geben Sie Ihre Antwort ein (oder 'SKIP' zum Beenden)...",
        "error_pdf": "PDF-Generierung fehlgeschlagen: {error}",
        "error_system": "Systemfehler: {error}",
        "error_api_key": "API-Schlüssel fehlt. Bitte setzen Sie GOOGLE_API_KEY in secrets."
    }
}

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
    except (OSError, IOError, json.JSONEncodeError) as e:
        # Silently fail logging - don't break the app if logging fails
        pass
# #endregion

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Einstein - behavioral self-assessment", 
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items=None
)   

# --- SESSION STATE MANAGEMENT ---
def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        "language": "en",
        "previous_language": "en",
        "messages": [],
        "chat_history": [],
        "show_final_results": False,
        "final_display_text": ""
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_conversation():
    """Reset conversation when language changes"""
    st.session_state.messages = []
    st.session_state.chat_history = []
    st.session_state.show_final_results = False
    st.session_state.final_display_text = ""

# Initialize session state FIRST (before API setup which uses language)
initialize_session_state()

# --- API SETUP ---
# Fetch key from secrets (works on Local and Streamlit Cloud)
def initialize_api():
    """Initialize Google Generative AI API"""
    # #region agent log
    debug_log("app.py:initialize_api", "API initialization started", {"language": st.session_state.get("language", "en")}, "H1")
    # #endregion
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # #region agent log
        debug_log("app.py:initialize_api", "API initialized successfully", {}, "H1")
        # #endregion
        return True
    except KeyError:
        # #region agent log
        debug_log("app.py:initialize_api", "API key missing", {"language": st.session_state.get("language", "en")}, "H1")
        # #endregion
        st.error(LANG_TEXTS[st.session_state.get("language", "en")]["error_api_key"])
        return False
    except Exception as e:
        # #region agent log
        debug_log("app.py:initialize_api", "API initialization error", {"error": str(e)}, "H1")
        # #endregion
        st.error(f"API initialization error: {e}")
        return False

if not initialize_api():
    st.stop()

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
4.  **Format:** Each question must be formatted as:
    **A)** [Option A text]
    **B)** [Option B text]
5.  **Tone:** Direct, clinical, no fluff. You are building a technical manual, not a self-help book.
6.  **Completion:** After question 40, output the marker "ANALYSIS_COMPLETE" followed immediately by the full User Manual in markdown format. The manual should be comprehensive, structured, and actionable.

**CRITICAL RULES:**
- Never ask two questions at once.
- Never skip the forced-choice format (A vs B).
- Never stop before 40 questions unless the user explicitly requests to skip.
- Always format options as **A)** and **B)** with markdown bold.
- When the user types "SKIP" or selects a skip option, immediately generate the final User Manual with the "ANALYSIS_COMPLETE" marker.
If the user types the exact phrase "SKIP_TO_REPORT" (or just "SKIP"), stop asking questions immediately.
Generate the final User Manual immediately. Use the marker "ANALYSIS_COMPLETE" followed by the full manual in markdown.
"""

# --- LANGUAGE CHANGE HANDLING ---
# Check if language changed and reset conversation if needed
if st.session_state.previous_language != st.session_state.language:
    # #region agent log
    debug_log("app.py:language_change", "Language changed", {"old": st.session_state.previous_language, "new": st.session_state.language}, "H2")
    # #endregion
    reset_conversation()
    st.session_state.previous_language = st.session_state.language

# --- HELPER FUNCTIONS ---
def get_language_text(key):
    """Get localized text for a given key"""
    lang = st.session_state.get("language", "en")
    return LANG_TEXTS[lang].get(key, LANG_TEXTS["en"].get(key, ""))

def create_chat_model():
    """Create and return a GenerativeModel instance"""
    return genai.GenerativeModel(MODEL_NAME)

def get_chat_session():
    """Get or create chat session with history"""
    model = create_chat_model()
    return model.start_chat(history=st.session_state.chat_history)

def send_message_with_language(prompt):
    """Send message to AI with language instruction"""
    # #region agent log
    debug_log("app.py:send_message", "Sending message to AI", {"prompt_length": len(prompt), "language": st.session_state.language}, "H2")
    # #endregion
    try:
        chat = get_chat_session()
        lang_note = f"\n[Respond in {'German' if st.session_state.language == 'de' else 'English'}]"
        response = chat.send_message(prompt + lang_note)
        st.session_state.chat_history = chat.history
        # #region agent log
        debug_log("app.py:send_message", "Message sent successfully", {"response_length": len(response.text)}, "H2")
        # #endregion
        return response.text
    except Exception as e:
        # #region agent log
        debug_log("app.py:send_message", "Error sending message", {"error": str(e), "error_type": type(e).__name__}, "H2")
        # #endregion
        raise e

def handle_analysis_complete(ai_text):
    """Handle when analysis is complete - extract text and prepare for display"""
    # #region agent log
    debug_log("app.py:handle_complete", "Analysis complete detected", {"ai_text_length": len(ai_text)}, "H1")
    # #endregion
    display_text = ai_text.replace(ANALYSIS_COMPLETE_MARKER, "").strip()
    st.session_state.final_display_text = display_text
    st.session_state.show_final_results = True
    # #region agent log
    debug_log("app.py:handle_complete", "Final display text prepared", {"display_text_length": len(display_text)}, "H1")
    # #endregion
    return display_text

def display_final_results(display_text):
    """Display final results with PDF download"""
    with st.chat_message("model"):
        st.markdown(display_text)
    st.success(get_language_text("finalized"))
    try:
        pdf_bytes = create_pdf(display_text)
        st.download_button(
            label=get_language_text("download"),
            data=pdf_bytes,
            file_name=PDF_FILENAME,
            mime="application/pdf"
        )
    except Exception as pdf_error:
        st.error(get_language_text("error_pdf").format(error=pdf_error))

def process_user_input(prompt, show_spinner=True):
    """Process user input and return AI response"""
    # #region agent log
    debug_log("app.py:process_user_input", "Processing user input", {"prompt": prompt, "prompt_length": len(prompt), "show_spinner": show_spinner, "messages_before": len(st.session_state.messages)}, "H2")
    # #endregion
    
    # Add user message to session state first
    st.session_state.messages.append({"role": "user", "content": prompt})
    # #region agent log
    debug_log("app.py:process_user_input", "User message added", {"messages_after_user": len(st.session_state.messages)}, "H2")
    # #endregion
    
    spinner_text = get_language_text("processing") if show_spinner else get_language_text("analyzing")
    with st.spinner(spinner_text):
        try:
            ai_text = send_message_with_language(prompt)
            # #region agent log
            debug_log("app.py:process_user_input", "AI response received", {"response_length": len(ai_text), "has_complete": ANALYSIS_COMPLETE_MARKER in ai_text, "response_preview": ai_text[:200]}, "H2")
            # #endregion
            
            # Add model response to session state
            st.session_state.messages.append({"role": "model", "content": ai_text})
            # #region agent log
            debug_log("app.py:process_user_input", "Model message added", {"messages_after_model": len(st.session_state.messages)}, "H2")
            # #endregion
            
            if ANALYSIS_COMPLETE_MARKER in ai_text:
                # Analysis complete - handle and rerun
                display_text = handle_analysis_complete(ai_text)
                # #region agent log
                debug_log("app.py:process_user_input", "Analysis complete, triggering rerun", {}, "H1")
                # #endregion
                st.rerun()
            else:
                # Normal question - rerun to refresh UI and show new buttons
                # #region agent log
                debug_log("app.py:process_user_input", "Normal question, triggering rerun", {}, "H2")
                # #endregion
                st.rerun()
            return True
        except Exception as e:
            # #region agent log
            debug_log("app.py:process_user_input", "Error processing input", {"error": str(e), "error_type": type(e).__name__}, "H2")
            # #endregion
            # Remove user message if processing failed to maintain state consistency
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                st.session_state.messages.pop()
                # #region agent log
                debug_log("app.py:process_user_input", "User message removed due to error", {"messages_after_removal": len(st.session_state.messages)}, "H2")
                # #endregion
            st.error(get_language_text("error_system").format(error=e))
            return False

# Start conversation if no messages exist
if len(st.session_state.messages) == 0:
    # Start the conversation with the system prompt hidden from view
    language_instruction = f"\n\n**CURRENT USER LANGUAGE:** {st.session_state.language.upper()}. Respond in {'German' if st.session_state.language == 'de' else 'English'}."
    full_system_prompt = SYSTEM_PROMPT + language_instruction
    model = create_chat_model()
    chat = model.start_chat(history=[])
    response = chat.send_message(full_system_prompt)
    st.session_state.messages.append({"role": "model", "content": response.text})
    st.session_state.chat_history = chat.history

# --- PDF GENERATOR FUNCTION ---
def create_pdf(text):
    """Create PDF from markdown text"""
    # #region agent log
    debug_log("app.py:create_pdf", "Creating PDF", {"text_length": len(text)}, "H3")
    # #endregion
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Set font
    pdf.set_font("Arial", size=11)
    
    lines = text.split('\n')
    in_list = False
    
    try:
        for line in lines:
            line = line.strip()
            
            # Skip empty lines (but add small spacing)
            if not line:
                if in_list:
                    in_list = False
                    pdf.ln(5)
                pdf.ln(3)
                continue
            
            # Handle headers (# ## ###)
            if line.startswith('#'):
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
                try:
                    text = f"• {list_item}".encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(170, 6, text, align='L')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    try:
                        text = f"• {list_item}".encode('utf-8', 'replace').decode('latin-1', 'replace')
                        pdf.multi_cell(170, 6, text, align='L')
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        pdf.multi_cell(170, 6, f"• {list_item}", align='L')
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
            # Calculate proper width (A4 width 210mm, minus 10mm left margin, minus 10mm right margin = 190mm)
            # FPDF uses mm by default
            page_width = 190
            try:
                # Better encoding handling with proper word wrapping
                text = line.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(page_width, 6, text, align='L')
            except Exception as e1:
                try:
                    text = line.encode('utf-8', 'replace').decode('latin-1', 'replace')
                    pdf.multi_cell(page_width, 6, text, align='L')
                except Exception as e2:
                    # Fallback: try without encoding
                    try:
                        pdf.multi_cell(page_width, 6, str(line), align='L')
                    except Exception as e3:
                        # Last resort: use default width
                        try:
                            pdf.multi_cell(0, 6, str(line), align='L')
                        except Exception:
                            # Ultimate fallback: skip problematic line
                            pass
            
            pdf.ln(3)
        
        # Add page numbers
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Output PDF as bytes
        try:
            return pdf.output(dest='S')
        except UnicodeEncodeError as e:
        # #region agent log
            debug_log("app.py:create_pdf", "Unicode encoding error, trying direct output", {"error": str(e)}, "H3")
            # #endregion
            # Fallback: return as bytes directly
            try:
                return pdf.output(dest='S')
            except Exception as e2:
                # #region agent log
                debug_log("app.py:create_pdf", "PDF output failed, creating fallback", {"error": str(e2)}, "H3")
                # #endregion
                # Last resort: create minimal PDF
                pdf_fallback = FPDF()
                pdf_fallback.add_page()
                pdf_fallback.set_font("Arial", size=12)
                pdf_fallback.multi_cell(0, 10, "Error generating PDF. Please try again.")
                return pdf_fallback.output(dest='S')
    except Exception as e:
        # #region agent log
        debug_log("app.py:create_pdf", "Unexpected PDF error", {"error": str(e), "error_type": type(e).__name__}, "H3")
        # #endregion
        # Last resort: create minimal PDF
        pdf_fallback = FPDF()
        pdf_fallback.add_page()
        pdf_fallback.set_font("Arial", size=12)
        pdf_fallback.multi_cell(0, 10, "Error generating PDF. Please try again.")
        return pdf_fallback.output(dest='S')

# --- UI LAYOUT ---
# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Global Font - System Stack for speed and cleanliness */
    * { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    
    /* Background & Main Layout */
    .stApp { background-color: #FAFAFA; }
    .main .block-container { max-width: 900px; padding-top: 2rem; padding-bottom: 5rem; }

    /* HIDE STREAMLIT ELEMENTS */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stChatMessage [data-testid="stChatMessageAvatar"] { display: none !important; }

    /* TYPOGRAPHY */
    h1 { font-weight: 700; letter-spacing: -1px; color: #111; }
    p { font-size: 1.05rem; line-height: 1.6; color: #333; }

    /* CHAT BUBBLES - "The Monolith" Look */
    .stChatMessage {
        background-color: transparent;
        border: none;
        padding: 0;
        margin-bottom: 2rem;
    }

    /* User Message - Minimalist Right Alignment */
    .stChatMessage[data-testid="user"] {
        background-color: #f0f0f0;
        border-radius: 12px 12px 0 12px;
        padding: 1rem 1.5rem;
        max-width: 70%;
        margin-left: auto;
    }
    .stChatMessage[data-testid="user"] p { color: #111 !important; }

    /* AI Message - Clean Typography, No Box */
    .stChatMessage[data-testid="assistant"] {
        background-color: white;
        border-left: 4px solid #000; /* The Monolith Stripe */
        padding: 1rem 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border-radius: 0 12px 12px 0;
    }

    /* BUTTONS - High Contrast */
    .stButton > button {
        background-color: white;
        color: #111;
        border: 2px solid #111;
        border-radius: 4px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #111;
        color: white;
        border-color: #111;
        transform: translateY(-2px);
    }
    
    /* All Buttons - Match language button style exactly (white with light gray border) */
    button[data-testid*="btn_a_"],
    button[data-testid*="btn_b_"],
    button[data-testid*="skip_btn"],
    button[data-testid*="lang_btn"],
    .stButton > button[data-testid*="btn_a_"],
    .stButton > button[data-testid*="btn_b_"],
    .stButton > button[data-testid*="skip_btn"],
    .stButton > button[data-testid*="lang_btn"] {
        background-color: white !important;
        color: #111 !important;
        border: 1px solid #ddd !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    button[data-testid*="btn_a_"]:hover,
    button[data-testid*="btn_b_"]:hover,
    button[data-testid*="skip_btn"]:hover,
    button[data-testid*="lang_btn"]:hover,
    .stButton > button[data-testid*="btn_a_"]:hover,
    .stButton > button[data-testid*="btn_b_"]:hover,
    .stButton > button[data-testid*="skip_btn"]:hover,
    .stButton > button[data-testid*="lang_btn"]:hover {
        background-color: #f8f9fa !important;
        color: #111 !important;
        border-color: #ccc !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }

    /* INFO BOXES (For A/B Options) */
    .stAlert {
        background-color: #fff;
        border: 1px solid #ddd;
        border-radius: 8px;
    }
</style>
<script>
    // Mark selected buttons as black
    window.addEventListener('load', function() {
        // Check session state for selected options and style buttons accordingly
        // This runs after Streamlit renders the buttons
        setTimeout(function() {
            const buttons = document.querySelectorAll('button[data-testid*="btn_a_"], button[data-testid*="btn_b_"]');
            buttons.forEach(function(btn) {
                // Check if button was recently clicked (within last second)
                btn.addEventListener('click', function() {
                    // Remove selected class from sibling buttons
                    const allOptionButtons = document.querySelectorAll('button[data-testid*="btn_a_"], button[data-testid*="btn_b_"]');
                    allOptionButtons.forEach(function(b) {
                        b.classList.remove('option-selected');
                    });
                    // Add selected class to clicked button
                    this.classList.add('option-selected');
                });
            });
        }, 100);
    });
</script>
<style>
    /* Selected option button - black background (when clicked) */
    button.option-selected[data-testid*="btn_a_"],
    button.option-selected[data-testid*="btn_b_"],
    .stButton > button.option-selected[data-testid*="btn_a_"],
    .stButton > button.option-selected[data-testid*="btn_b_"] {
        background-color: #111 !important;
        color: white !important;
        border: 1px solid #111 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- DEBUGGING TOOL (IN DIE SIDEBAR) ---
with st.sidebar:
    st.divider()
    st.header("🕵️ Model Scanner")
    if st.button("Check Available Models"):
        try:
            st.write("Asking Google API...")
            found_any = False
            # Wir fragen die API, was verfügbar ist
            for m in genai.list_models():
                # Wir zeigen nur Modelle, die Text generieren können
                if 'generateContent' in m.supported_generation_methods:
                    st.code(m.name) # Zeigt den exakten Namen (z.B. models/gemini-1.5-flash)
                    found_any = True
            
            if not found_any:
                st.error("No models found via API.")
        except Exception as e:
            st.error(f"Error listing models: {e}")

# --- UI LAYOUT ---
col_title, col_controls = st.columns([2, 1])

with col_title:
    st.title("Einstein Protocol")
    st.caption("Monolithic Behavioral Architecture")

with col_controls:
    # Use a container to right-align contents
    with st.container():
        # Create small columns for the controls to sit side-by-side compact
        c1, c2 = st.columns(2)
        with c1:
            # Language Toggle
            current_lang = st.session_state.language
            new_lang = "de" if current_lang == "en" else "en"
            label = "🇩🇪 DE" if current_lang == "en" else "🇬🇧 EN"
            if st.button(label, key="lang_btn", help="Switch Language"):
                st.session_state.previous_language = current_lang
                st.session_state.language = new_lang
                reset_conversation()
                st.rerun()
        with c2:
            # Skip Button (Icon style)
            if st.button("⏩ Skip", key="skip_btn", type="secondary"):
                # #region agent log
                debug_log("app.py:skip", "Skip button clicked", {"language": st.session_state.language}, "H1")
                # #endregion
                process_user_input("SKIP", show_spinner=True)

def detect_ab_options(content):
    """Detect A/B options in message content using multiple regex patterns"""
    # #region agent log
    debug_log("app.py:detect_ab_options", "Detecting A/B options", {"content_length": len(content), "content_preview": content[:200]}, "H4")
    # #endregion
    
    a_match = None
    b_match = None
    
    # Pattern 1: "**A)**" format (with markdown bold - most common)
    a_match = re.search(r'\*\*A\)\*\*\s+(.+?)(?=\s*\*\*B\)\*\*|$)', content, re.IGNORECASE | re.DOTALL)
    b_match = re.search(r'\*\*B\)\*\*\s+(.+?)(?=\n\s*(?:Choose|$)|$)', content, re.IGNORECASE | re.DOTALL)
    
    # Pattern 2: "A)" or "B)" format (without markdown)
    if not (a_match and b_match):
        a_match = re.search(r'(?:^|\n)\s*A\)\s+(.+?)(?=\s*B\)|$)', content, re.IGNORECASE | re.DOTALL)
        b_match = re.search(r'(?:^|\n)\s*B\)\s+(.+?)(?=\n\s*(?:Choose|$)|$)', content, re.IGNORECASE | re.DOTALL)
    
    # Pattern 3: "A:" or "A)" or "Option A:" format
    if not (a_match and b_match):
        a_match = re.search(r'(?:^|\n)\s*(?:Option\s+)?A[:\-)]\s+(.+?)(?=\n\s*(?:Option\s+)?B|$)', content, re.IGNORECASE | re.DOTALL)
        b_match = re.search(r'(?:^|\n)\s*(?:Option\s+)?B[:\-)]\s+(.+?)(?=\n|$)', content, re.IGNORECASE | re.DOTALL)
    
    # Pattern 4: "**A**" or "**Option A**" format (without parenthesis)
    if not (a_match and b_match):
        a_match = re.search(r'\*\*A\*\*[:\s]+(.+?)(?=\*\*B\*\*|\n\s*\*\*B\*\*|$)', content, re.IGNORECASE | re.DOTALL)
        b_match = re.search(r'\*\*B\*\*[:\s]+(.+?)(?=\n|$)', content, re.IGNORECASE | re.DOTALL)
    
    # Pattern 5: Try "A." or "B." format
    if not (a_match and b_match):
        a_match = re.search(r'(?:^|\n)\s*A\.\s+(.+?)(?=\n\s*B\.|$)', content, re.IGNORECASE | re.DOTALL)
        b_match = re.search(r'(?:^|\n)\s*B\.\s+(.+?)(?=\n|$)', content, re.IGNORECASE | re.DOTALL)
    
    # Pattern 6: More flexible - find all A) and B) patterns
    if not (a_match and b_match):
        a_matches = list(re.finditer(r'(?:^|\n)\s*A\)\s+(.+?)(?=\n|$)', content, re.IGNORECASE | re.DOTALL))
        b_matches = list(re.finditer(r'(?:^|\n)\s*B\)\s+(.+?)(?=\n|$)', content, re.IGNORECASE | re.DOTALL))
        if a_matches and b_matches:
            # Use the last A) and B) found (most likely to be the question options)
            a_match = a_matches[-1]
            b_match = b_matches[-1]
    
    # #region agent log
    debug_log("app.py:detect_ab_options", "Detection complete", {"a_match": a_match is not None, "b_match": b_match is not None, "a_text": a_match.group(1)[:50] if a_match else None, "b_text": b_match.group(1)[:50] if b_match else None}, "H4")
    # #endregion
    
    return a_match, b_match

def format_question_with_line_breaks(content, remove_options=False):
    """Ensure A) and B) options appear on separate lines and remove markdown formatting.
    If remove_options is True, remove the A) and B) options from the content."""
    # Remove all ** markdown bold formatting
    content = re.sub(r'\*\*', '', content)
    
    if remove_options:
        # Remove A) and B) options from the content (they'll be shown in info boxes instead)
        content = re.sub(r'\n?\s*\*\*?A\)\*\*?\s*.*?(?=\n\s*\*\*?B\)|$)', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'\n?\s*\*\*?B\)\*\*?\s*.*?$', '', content, flags=re.IGNORECASE | re.DOTALL)
        # Also handle formats without markdown
        content = re.sub(r'\n?\s*A\)\s*.*?(?=\n\s*B\)|$)', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'\n?\s*B\)\s*.*?$', '', content, flags=re.IGNORECASE | re.DOTALL)
    else:
        # Add line break before A) if it's not already on a new line
        content = re.sub(r'([^\n])\s*(A\)|A:|Option A)', r'\1\n\n\2', content, flags=re.IGNORECASE)
        # Add line break before B) if it's not already on a new line  
        content = re.sub(r'([^\n])\s*(B\)|B:|Option B)', r'\1\n\n\2', content, flags=re.IGNORECASE)
    
    return content

# Check if we need to show final results (after skip)
if st.session_state.get("show_final_results", False) and st.session_state.get("final_display_text"):
    display_final_results(st.session_state.final_display_text)
    st.session_state.show_final_results = False

# Display Chat History with better spacing
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message["role"] != "system": # Don't show the hidden system prompt
            # Skip messages that contain ANALYSIS_COMPLETE (we show them separately above)
            if ANALYSIS_COMPLETE_MARKER in message.get("content", ""):
                continue
            with st.chat_message(message["role"]):
                # Format model messages - remove A/B options if they're shown as buttons below
                if message["role"] == "model":
                    # Check if this is the last message and has A/B options that will be shown as buttons
                    is_last_message = message == st.session_state.messages[-1] if st.session_state.messages else False
                    has_options = False
                    if is_last_message and ANALYSIS_COMPLETE_MARKER not in message.get("content", ""):
                        # Check if options will be displayed as buttons
                        a_match, b_match = detect_ab_options(message["content"])
                        has_options = a_match is not None and b_match is not None
                    
                    # Remove options from display if they're shown as buttons
                    formatted_content = format_question_with_line_breaks(message["content"], remove_options=has_options)
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
    if last_message["role"] == "model" and ANALYSIS_COMPLETE_MARKER not in last_message["content"]:
        content = last_message["content"]
        # #region agent log
        debug_log("app.py:check_last_message", "Checking last message for A/B options", {"content_length": len(content), "content_preview": content[:200]}, "H5")
        # #endregion
        
        # Use helper function to detect A/B options
        a_match, b_match = detect_ab_options(content)
        
        if a_match and b_match:
            show_buttons = True
            option_a = a_match.group(1).strip()
            option_b = b_match.group(1).strip()
            # Clean up the options (remove markdown, limit length)
            option_a = re.sub(r'\*\*', '', option_a)[:150]
            option_b = re.sub(r'\*\*', '', option_b)[:150]
            # #region agent log
            debug_log("app.py:options_detected", "A/B options detected and cleaned", {"option_a": option_a[:50], "option_b": option_b[:50], "option_a_len": len(option_a), "option_b_len": len(option_b)}, "H5")
            # #endregion
        else:
            # #region agent log
            debug_log("app.py:options_not_detected", "A/B options NOT detected", {"a_match": a_match is not None, "b_match": b_match is not None}, "H5")
            # #endregion

# Show buttons if A/B options detected, otherwise show text input
# #region agent log
debug_log("app.py:432", "Before button display check", {"show_buttons": show_buttons, "option_a": option_a is not None, "option_b": option_b is not None}, "H5")
# #endregion
if show_buttons:
    # #region agent log
    debug_log("app.py:435", "Entering button display block", {"option_a": option_a is not None, "option_b": option_b is not None, "option_a_value": option_a[:30] if option_a else None, "option_b_value": option_b[:30] if option_b else None}, "H5")
    # #endregion
    
    if option_a and option_b:
        # #region agent log
        debug_log("app.py:441", "Displaying option buttons", {}, "H5")
        # #endregion
        
        st.markdown("### Choose your path:")
        col1, col2 = st.columns(2, gap="medium")
        
        # We use a custom key combining the message count to ensure uniqueness/reset
        step_id = len(st.session_state.messages)

        with col1:
            # Display the text clearly, then the button
            st.info(f"**A)** {option_a}")
            if st.button("Select Option A", key=f"btn_a_{step_id}", use_container_width=True, type="secondary"):
                # #region agent log
                debug_log("app.py:button_a", "Button A clicked", {"messages_count": len(st.session_state.messages), "last_message_preview": st.session_state.messages[-1]["content"][:100] if st.session_state.messages else None}, "H2")
                # #endregion
                process_user_input(f"Option A: {option_a}", show_spinner=True)

        with col2:
            st.info(f"**B)** {option_b}")
            if st.button("Select Option B", key=f"btn_b_{step_id}", use_container_width=True, type="secondary"):
                # #region agent log
                debug_log("app.py:button_b", "Button B clicked", {"messages_count": len(st.session_state.messages), "last_message_preview": st.session_state.messages[-1]["content"][:100] if st.session_state.messages else None}, "H2")
                # #endregion
                process_user_input(f"Option B: {option_b}", show_spinner=True)
    else:
        # #region agent log
        debug_log("app.py:576", "Option A or B is None/empty", {"option_a": option_a, "option_b": option_b}, "H5")
        # #endregion
        # Edge case: show_buttons is True but options are incomplete - show fallback input
        analysis_complete = False
        if st.session_state.messages:
            last_message = st.session_state.messages[-1]
            if ANALYSIS_COMPLETE_MARKER in last_message.get("content", ""):
                analysis_complete = True
        
        showing_final_results = st.session_state.get("show_final_results", False) or bool(st.session_state.get("final_display_text", ""))
        
        if not analysis_complete and not showing_final_results:
            # #region agent log
            debug_log("app.py:fallback_input_incomplete", "Showing fallback input (incomplete options)", {"show_buttons": show_buttons, "option_a": option_a, "option_b": option_b}, "H5")
            # #endregion
            if prompt := st.chat_input(get_language_text("chat_placeholder")):
                process_user_input(prompt, show_spinner=False)

# Fallback: text input if no buttons are shown and analysis is not complete
if not show_buttons:
    # Check if analysis is complete or final results are being shown
    analysis_complete = False
    if st.session_state.messages:
        last_message = st.session_state.messages[-1]
        if ANALYSIS_COMPLETE_MARKER in last_message.get("content", ""):
            analysis_complete = True
    
    showing_final_results = st.session_state.get("show_final_results", False) or bool(st.session_state.get("final_display_text", ""))
    
    # Only show text input if analysis is not complete and final results are not being displayed
    if not analysis_complete and not showing_final_results:
        # #region agent log
        debug_log("app.py:fallback_input", "Showing fallback text input", {"show_buttons": show_buttons, "analysis_complete": analysis_complete, "showing_final_results": showing_final_results}, "H5")
        # #endregion
        if prompt := st.chat_input(get_language_text("chat_placeholder")):
            process_user_input(prompt, show_spinner=False)

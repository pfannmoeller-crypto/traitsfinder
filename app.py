import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="The Monolithic Assessment", layout="centered")

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

**THE PROTOCOL:**
1.  **One by One:** Ask strictly ONE question at a time. Wait for the answer.
2.  **Forced Choice:** Use Ipsative (A vs B) scenarios. Force difficult trade-offs.
3.  **Phase 1 (Discovery):** Ask ~5 questions to map the baseline.
4.  **Phase 2 (Stress Test):** Ask ~3 questions placing them in high-pressure scenarios.
5.  **Phase 3 (Analysis):** When you have enough data (approx 8-10 turns), stop asking questions.
    * Output the text "ANALYSIS_COMPLETE" alone on a new line.
    * Then, generate the "Comprehensive User Manual" in strict Markdown format.
    * Include sections: "I. The Architecture", "II. Contextual Contrasts", "III. Environment Fit", "IV. Operational Rules".
    * Write in the tone of a "Sovereign Architect": direct, professional, and slightly clinical.

Start immediately by introducing yourself briefly as "The Monolithic Architect" and asking Question 1.
"""

# --- SESSION STATE MANAGEMENT ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Start the conversation with the system prompt hidden from view
    model = genai.GenerativeModel('gemini-1.5-pro')
    chat = model.start_chat(history=[])
    response = chat.send_message(SYSTEM_PROMPT)
    st.session_state.messages.append({"role": "model", "content": response.text})
    st.session_state.chat_history = chat.history # Save the gemini object history

# --- PDF GENERATOR FUNCTION ---
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    
    # Simple formatting: split by lines and write
    # (For a real app, you'd want more complex Markdown parsing)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Your Monolithic User Manual", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    # Encode text to latin-1 for FPDF (handles some special chars)
    # Replacing common markdown markers for clean text
    clean_text = text.replace("**", "").replace("##", "").replace("###", "")
    
    for line in clean_text.split('\n'):
        try:
            pdf.multi_cell(0, 10, line.encode('latin-1', 'replace').decode('latin-1'))
        except:
            pdf.multi_cell(0, 10, line)
            
    return pdf.output(dest='S').encode('latin-1')

# --- UI LAYOUT ---
st.title("The Monolithic System")
st.caption("Optimization & Compatibility Protocols v2.1")

# Display Chat History
for message in st.session_state.messages:
    if message["role"] != "system": # Don't show the hidden system prompt
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# User Input Handling
if prompt := st.chat_input("Enter your response..."):
    # 1. Display User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Get AI Response
    with st.spinner("Analyzing Architecture..."):
        try:
            # Reconstruct chat session
            model = genai.GenerativeModel('gemini-1.5-pro')
            chat = model.start_chat(history=st.session_state.chat_history)
            
            response = chat.send_message(prompt)
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
                st.success("System Analysis Finalized.")
                pdf_bytes = create_pdf(display_text)
                st.download_button(
                    label="Download Your User Manual (PDF)",
                    data=pdf_bytes,
                    file_name="My_Monolithic_Manual.pdf",
                    mime="application/pdf"
                )
            else:
                # Normal Question Flow
                with st.chat_message("model"):
                    st.markdown(ai_text)
                    
        except Exception as e:
            st.error(f"System Error: {e}")

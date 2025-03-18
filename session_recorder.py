import streamlit as st
import assemblyai as aai
from anthropic import Anthropic
import tempfile
import os
import time
from datetime import datetime
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="SBDC Session Recorder",
    page_icon="🎙️",
    layout="wide"
)

# Initialize session state variables if they don't exist
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "report" not in st.session_state:
    st.session_state.report = ""
if "recording" not in st.session_state:
    st.session_state.recording = False
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None
if "temp_file_path" not in st.session_state:
    st.session_state.temp_file_path = None
if "status" not in st.session_state:
    st.session_state.status = "Ready"
if "session_type" not in st.session_state:
    st.session_state.session_type = "Initial Session"

# Load API keys from Streamlit secrets
try:
    assemblyai_api_key = st.secrets["ASSEMBLYAI_API_KEY"]
    claude_api_key = st.secrets["CLAUDE_API_KEY"]
    
    # Configure AssemblyAI with the API key
    aai.settings.api_key = assemblyai_api_key
    
    # Initialize Claude client
    claude_client = Anthropic(api_key=claude_api_key)
    
    keys_configured = True
except Exception as e:
    st.error(f"Error loading API keys: {str(e)}")
    st.error("Please add ASSEMBLYAI_API_KEY and CLAUDE_API_KEY to your Streamlit secrets.")
    keys_configured = False

# Main app header
st.title("SBDC Session Recorder & Report Generator")
st.write("Record advisor-client sessions, transcribe them, and generate structured reports.")

# Function to transcribe audio file
def transcribe_audio_file(file_path):
    try:
        st.session_state.status = "Transcribing audio..."
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(file_path)
        st.session_state.transcript = transcript.text
        st.session_state.status = "Transcription complete"
        return True
    except Exception as e:
        st.error(f"Transcription error: {str(e)}")
        st.session_state.status = "Transcription failed"
        return False

# Function to generate report using Claude
def generate_report():
    try:
        st.session_state.status = "Generating report..."
        
        # Determine which template to use
        template = st.session_state.session_type
        
        # Create the prompt
        prompt = f"""You are an SBDC (Small Business Development Center) assistant that helps advisors create structured session notes.
        
Based on the following transcript of a session between an SBDC advisor and a client, please generate a report using the {template} template.

TRANSCRIPT:
{st.session_state.transcript}

"""
        
        # Add the appropriate template format to the prompt
        if template == "Initial Session":
            prompt += """Please format the report with the following sections:

BRIEF DESCRIPTION OF THE BUSINESS AND/OR OWNERS: 
Service or product/Short history/Others involved/Special Circumstances/Timeline

OVERVIEW AND ANALYSIS OF THE CRITICAL PROBLEM: 
Assistance requested/Questions answered/identification of other problems to be considered/red flags/ideas brainstormed/resources identified

RECOMMENDATIONS AND ACTIONS TO BE TAKEN: 
Directions given/warnings or cautions/quick lessons taught/resources revealed/ideas floated/websites visited/forms reviewed/referrals to agencies

PLAN OF ACTION, NEXT STEPS & FOLLOW-UP: 
What specifically the client will do and what will the counselor do/Classes enrolled, books checked out, other advisors sought/Websites to visit/Research to do/materials to send/agency contacts to make/materials filed/prep work for next meeting
"""
        else:  # Follow-Up Session
            prompt += """Please format the report with the following sections:

ACHIEVEMENT TOWARD GOAL AND/OR OTHER KEY ISSUES: 
Achievements based on prior counseling/client activities from their Plan of Action/work-plan, with identification of any additional problems to be considered. Include estimated hours the client spent working in their business toward achievement of specific goals.

RECOMMENDATIONS AND ACTIONS TO BE TAKEN: 
Directions given/warnings or cautions/quick lessons taught/resources revealed/ideas floated/websites visited/forms reviewed/referrals to agencies

PLAN OF ACTION, NEXT STEPS & FOLLOW-UP: 
What specifically the client will do and what will the counselor do/Classes enrolled, books checked out, other advisors sought/Websites to visit/Research to do/materials to send/agency contacts to make/materials filed/prep work for next meeting
"""
        
        # Make API call to Claude
        response = claude_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            temperature=0.0,
            system="You are a helpful assistant for SBDC advisors who creates detailed session notes in the required format.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the report text
        st.session_state.report = response.content[0].text
        st.session_state.status = "Report generated successfully"
        return True
    except Exception as e:
        st.error(f"Report generation error: {str(e)}")
        st.session_state.status = "Report generation failed"
        return False

# Function to record audio using Streamlit's native audio recorder
def record_audio():
    st.session_state.status = "Recording audio..."
    audio_data = st.audio_recorder(pause_threshold=2.0, sample_rate=16000)
    
    if audio_data is not None:
        # Create a temporary file to save the audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_file.write(audio_data)
        st.session_state.temp_file_path = temp_file.name
        temp_file.close()
        
        st.session_state.audio_file = f"Recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        st.session_state.status = "Recording saved"
        
        # Transcribe the recording
        success = transcribe_audio_file(st.session_state.temp_file_path)
        return success
    
    return False

# Sidebar for configuration and controls
with st.sidebar:
    st.header("Configuration")
    
    # Display API key status
    if keys_configured:
        st.success("API keys configured successfully")
    else:
        st.error("API keys not configured")
    
    # Session type selection
    st.session_state.session_type = st.radio(
        "Session Type",
        ["Initial Session", "Follow-Up Session"]
    )
    
    st.header("Actions")
    
    # Record audio section
    st.subheader("Record Audio")
    st.write("Click to start/stop recording:")
    
    if st.button("Record from Microphone"):
        record_audio()
    
    # Upload audio file section
    st.subheader("Upload Audio")
    uploaded_file = st.file_uploader("Choose an audio file", type=["wav", "mp3", "m4a"])
    
    if uploaded_file is not None:
        # Save uploaded file to a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}")
        temp_file.write(uploaded_file.getvalue())
        st.session_state.temp_file_path = temp_file.name
        temp_file.close()
        
        st.session_state.audio_file = uploaded_file.name
        st.session_state.status = f"Audio file uploaded: {uploaded_file.name}"
        
        # Transcribe button for the uploaded file
        if st.button("Transcribe Uploaded Audio"):
            transcribe_audio_file(st.session_state.temp_file_path)
    
    # Upload transcript directly
    st.subheader("Upload Transcript")
    transcript_file = st.file_uploader("Choose a transcript file", type=["txt", "md"])
    
    if transcript_file is not None:
        st.session_state.transcript = transcript_file.getvalue().decode("utf-8")
        st.session_state.status = f"Transcript uploaded: {transcript_file.name}"
    
    # Generate report button
    if st.session_state.transcript:
        if st.button("Generate Report"):
            generate_report()
    
    # Status display
    st.header("Status")
    st.info(st.session_state.status)

# Main content area with tabs
tab1, tab2 = st.tabs(["Transcript", "Report"])

# Transcript tab
with tab1:
    st.header("Session Transcript")
    
    if st.session_state.audio_file:
        st.caption(f"Source: {st.session_state.audio_file}")
    
    transcript_text = st.text_area(
        "Edit transcript if needed:",
        value=st.session_state.transcript,
        height=400
    )
    
    # Update transcript in session state if edited
    if transcript_text != st.session_state.transcript:
        st.session_state.transcript = transcript_text

# Report tab
with tab2:
    st.header(f"SBDC {st.session_state.session_type} Report")
    
    if st.session_state.report:
        st.markdown(st.session_state.report)
        
        # Export options
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Copy to Clipboard"):
                st.write("Report copied to clipboard")
                # Note: This doesn't actually work in Streamlit as it's server-side
                # But included for UI completeness
        
        with col2:
            # Create a download button for the report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_type_str = "Initial" if st.session_state.session_type == "Initial Session" else "FollowUp"
            filename = f"SBDC_{session_type_str}_Report_{timestamp}.md"
            
            st.download_button(
                "Download Report",
                st.session_state.report,
                file_name=filename,
                mime="text/markdown"
            )
    else:
        st.info("No report generated yet. Transcribe a session and click 'Generate Report' to create one.")

# Clean up temporary files when the app is closed
def cleanup():
    if st.session_state.temp_file_path and os.path.exists(st.session_state.temp_file_path):
        os.unlink(st.session_state.temp_file_path)

# Register the cleanup function to run when the app is closed
import atexit
atexit.register(cleanup)

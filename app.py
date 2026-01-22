import streamlit as st
import tempfile
import os
from utils.llm_engine import analyze_and_structure_text
from utils.ppt_engine import create_presentation

# --- CONFIGURATION ---
st.set_page_config(page_title="Text to PPTX Generator", layout="wide", page_icon="✨")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* Global App Style replace default background */
    .stApp {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* Modern Header Container */
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    .header-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
    }
    .header-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }

    /* Card Styling */
    .stCard {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #f1f5f9;
        padding-top: 1rem;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #1e293b;
    }
    
    /* Custom Inputs */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 8px;
        border: 1px solid #cbd5e1;
    }
    .stTextArea textarea {
        border-radius: 12px;
        border: 1px solid #cbd5e1;
        font-size: 1rem;
        padding: 1rem;
    }
    
    /* Primary Gradient Button */
    div.stButton > button {
        background: linear-gradient(90deg, #4F46E5 0%, #6366f1 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.5rem;
        border-radius: 50px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(79, 70, 229, 0.2);
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px rgba(79, 70, 229, 0.3);
    }
    
    /* Slide Preview Cards */
    .slide-card {
        border-left: 4px solid #4F46E5;
        background: #f8fafc;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.5rem;
    }

    /* Custom Success/Error */
    .stAlert {
        border-radius: 10px;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.8rem;
        margin-top: 4rem;
        padding: 2rem 0;
        border-top: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state (Logic Untouched)
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "slides_data" not in st.session_state:
    st.session_state.slides_data = None

# --- HEADER SECTION ---
st.markdown("""
    <div class="header-container">
        <div class="header-title">✨ AI Presentation Generator</div>
        <div class="header-subtitle">Transform your ideas into professional PowerPoint decks in seconds.</div>
    </div>
""", unsafe_allow_html=True)

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # 1. AI Provider
    st.markdown("#### 🧠 AI Model")
    provider = st.selectbox(
        "Select Provider",
        ["Google Gemini", "OpenAI", "Anthropic"],
        label_visibility="collapsed"
    )
    
    st.markdown("#### 🔑 API Key")
    api_key = st.text_input(
        "API Key",
        type="password", 
        placeholder=f"Paste {provider} Key",
        label_visibility="collapsed"
    )

    st.info("🔒 Keys are processed securely in memory.")

    st.markdown("---")
    
    # 2. Tone / Style
    st.markdown("#### 🎨 Style & Tone")
    guidance = st.text_input("Guidance", placeholder="e.g., Investor Pitch, Educational...")

    st.caption("⚡ Quick Presets:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💼 Corp"): guidance = "Corporate Professional"
        if st.button("🎓 Edu"): guidance = "Educational and Detailed"
    with col2:
        if st.button("🚀 Startup"): guidance = "Investor Pitch Deck"
        if st.button("🎤 Story"): guidance = "Engaging and Visual"

    st.markdown("---")

    # 3. Template
    st.markdown("#### 📂 Design Template")
    upload_placeholder = st.empty()
    uploaded_template = upload_placeholder.file_uploader(
        "Upload Template", 
        type=["pptx", "potx"],
        key=f"template_uploader_{st.session_state.uploader_key}",
        label_visibility="collapsed"
    )

    # Logic to hide uploader and show selected file
    if uploaded_template:
        upload_placeholder.empty()
        st.success(f"✅ Active: {uploaded_template.name}")
        if st.button("↺ Change Template"):
            st.session_state.uploader_key += 1
            st.rerun()

# --- MAIN CONTENT ---

col1, col2 = st.columns([2, 1])

# Input Section
st.markdown("### 📝 Your Content")
input_text = st.text_area(
    "Content Input", 
    height=400, 
    placeholder="Paste your report, notes, or article here to convert it into slides...",
    label_visibility="collapsed"
)

# Action Area
col_act1, col_act2 = st.columns([1, 4])
with col_act1:
    generate_clicked = st.button("🚀 Generate Preview", use_container_width=True)

# Step 1: Analyze & Preview Logic
if generate_clicked:
    if not api_key:
        st.error(f"⚠️ Please enter your {provider} API Key in the sidebar.")
    elif not uploaded_template:
        st.error("⚠️ Please upload a .pptx template file in the sidebar.")
    elif not input_text:
        st.error("⚠️ Please enter text to convert.")
    else:
        with st.spinner("🔮 AI is analyzing structure and designing slides..."):
            # Estimate Slides
            est_slides = max(1, len(input_text) // 500)
            
            # Get JSON (Logic Untouched)
            data = analyze_and_structure_text(provider, api_key, input_text, guidance or "Professional", est_slides)
            
            if data:
                st.session_state.slides_data = data
                st.success("✨ Structure successfully generated! Review the plan below.")
            else:
                st.error("❌ Failed to generate structure. Please check the API key or text.")

# Step 2: Display Preview & Download
if st.session_state.slides_data:
    st.markdown("---")
    st.markdown("### 🎞️ Slide Plan Preview")
    
    # Create a grippy layout for cards
    for i, slide in enumerate(st.session_state.slides_data):
        with st.expander(f"Slide {i+1}: {slide.get('title', 'Untitled')}", expanded=False):
            st.markdown(f"""
            <div class="slide-card">
                <b>Title:</b> {slide.get('title', 'Untitled')}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**Content Points:**")
            for point in slide.get('content', []):
                st.write(f"• {point}")
            
            st.markdown(f"**🗣️ Speaker Notes:** _{slide.get('notes', 'No notes')}_")

    st.markdown("---")
    
    # Final Action
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("📥 Download Final PowerPoint", type="primary", use_container_width=True):
            with st.spinner("🎨 Assembling your mastery..."):
                try:
                    # Save Temp Template
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp_file:
                        tmp_file.write(uploaded_template.getvalue())
                        tmp_path = tmp_file.name
                    
                    # Generate (Logic Untouched)
                    output_file = create_presentation(tmp_path, st.session_state.slides_data)
                    
                    # Re-read for download
                    with open(output_file, "rb") as f:
                        file_data = f.read()

                    st.balloons()
                    st.download_button(
                        label="📄 Click to Save .pptx",
                        data=file_data,
                        file_name="generated_deck.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )

                    # Cleanup
                    if os.path.exists(output_file): os.remove(output_file)
                    if os.path.exists(tmp_path): os.remove(tmp_path)

                except Exception as e:
                    st.error(f"Error generating PPT: {e}")

# --- FOOTER ---
st.markdown("""
    <div class="footer">
        Built by Ram Bhajan Sahu — AI Presentation Generator<br>
        Powered by Gemini, OpenAI & Anthropic
    </div>
""", unsafe_allow_html=True)

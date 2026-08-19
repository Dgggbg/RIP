"""
AI Clinical Decision Support System - Streamlit Web UI
------------------------------------------------------
An interactive, modern clinical web interface for querying medical symptoms & guidelines,
built on top of local ChromaDB retrieval and Gemini grounded generation.

Run locally via:
    streamlit run app.py
"""

import os
import sys
import json
from pathlib import Path
import streamlit as st

# Set page configuration before any other Streamlit commands
st.set_page_config(
    page_title="AI Clinical Decision Support | Grounded RAG",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure current directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from query import load_index, retrieve
from generate import generate_grounded_answer
from ingest import load_pdfs, chunk_documents, build_index, get_embedding_function

# --- Inject Custom CSS for Premium Dark Clinical Aesthetics ---
st.markdown("""
<style>
    /* Global Styles & Dark Theme Accent */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main Background Accent */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    /* Card Styles */
    .medical-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
    }
    
    .recommendation-box {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.9) 100%);
        border-left: 5px solid #38bdf8;
        border-radius: 12px;
        padding: 20px;
        margin-top: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    
    .evidence-box {
        background: rgba(15, 23, 42, 0.6);
        border-left: 4px solid #a855f7;
        border-radius: 8px;
        padding: 16px;
        margin-top: 12px;
        font-style: italic;
        color: #e2e8f0;
    }

    /* Badges */
    .badge-high {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.4);
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    
    .badge-medium {
        background-color: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.4);
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    
    .badge-low {
        background-color: rgba(234, 179, 8, 0.2);
        color: #fde047;
        border: 1px solid rgba(253, 224, 71, 0.4);
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    
    .badge-insufficient {
        background-color: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid rgba(248, 113, 113, 0.4);
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }

    /* Citation Tag */
    .citation-tag {
        background: rgba(51, 65, 85, 0.8);
        color: #93c5fd;
        border: 1px solid rgba(147, 197, 253, 0.3);
        border-radius: 8px;
        padding: 8px 12px;
        margin: 4px 0;
        font-size: 0.88rem;
    }

    /* Sidebar Customization */
    section[data-testid="stSidebar"] {
        background: #0f172a;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---
def get_confidence_badge_html(confidence: str) -> str:
    conf = confidence.lower()
    if conf == "high":
        return '<span class="badge-high">🟢 High Confidence</span>'
    elif conf == "medium":
        return '<span class="badge-medium">🟠 Medium Confidence</span>'
    elif conf == "low":
        return '<span class="badge-low">🟡 Low Confidence</span>'
    else:
        return '<span class="badge-insufficient">🔴 Insufficient Evidence / Refusal</span>'


@st.cache_resource(show_spinner=False)
def get_vector_db():
    if not config.CHROMA_DIR.exists():
        return None
    try:
        return load_index()
    except Exception as e:
        st.error(f"Error loading Chroma DB: {e}")
        return None


# --- Sidebar Setup ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric/96/medical-heart.png", width=64)
    st.title("Clinical RAG Support")
    st.caption("AI-Powered Grounded Decision Support")
    st.markdown("---")
    
    st.subheader("⚙️ System Status")
    
    # Check DB Status
    db_exists = config.CHROMA_DIR.exists()
    if db_exists:
        st.success("✅ ChromaDB Index Ready")
    else:
        st.warning("⚠️ ChromaDB Index Not Found")
        
    # Check Gemini API Key
    api_key_set = bool(config.GEMINI_API_KEY)
    if api_key_set:
        st.success("✅ Gemini API Key Configured")
    else:
        st.error("❌ GEMINI_API_KEY Missing (.env)")
        
    st.markdown("---")
    st.markdown("**Active Configuration:**")
    st.write(f"- **Model:** `{config.GEMINI_MODEL}`")
    st.write(f"- **Embeddings:** `{config.EMBEDDING_PROVIDER}`")
    st.write(f"- **Top-K Retrieval:** `{config.TOP_K}` chunks")
    
    st.markdown("---")
    st.info("ℹ️ Answers are generated strictly from indexed clinical guidelines with full citation grounding.")


# --- Header ---
st.markdown("""
<div style="text-align: center; padding: 10px 0 30px 0;">
    <h1 style="font-weight: 700; background: linear-gradient(90deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        🩺 AI Clinical Decision Support Assistant
    </h1>
    <p style="color: #94a3b8; font-size: 1.1rem;">
        Type your medical symptoms or clinical questions to receive evidence-grounded recommendations from official guidelines.
    </p>
</div>
""", unsafe_allow_html=True)


# --- Tabs Navigation ---
tab_query, tab_upload, tab_diagnostics = st.tabs([
    "💬 Clinical Question & Symptom Query", 
    "📄 Document Management & Ingestion", 
    "📊 System Diagnostics"
])


# ==========================================
# TAB 1: CLINICAL QUESTION & SYMPTOM QUERY
# ==========================================
with tab_query:
    st.markdown("### 🔍 Enter Symptoms or Clinical Question")
    
    # Preset sample questions for rapid testing
    st.markdown("**Quick Sample Questions:**")
    col1, col2, col3 = st.columns(3)
    
    sample_selected = None
    with col1:
        if st.button("🩺 Hypertension Medication Target", use_container_width=True):
            sample_selected = "What blood pressure threshold should trigger starting medication?"
    with col2:
        if st.button("💊 First-line Drug Classes", use_container_width=True):
            sample_selected = "What are the recommended first-line drug classes for hypertension?"
    with col3:
        if st.button("📊 Cardiovascular Disease Target", use_container_width=True):
            sample_selected = "What is the target blood pressure for a patient with known cardiovascular disease?"

    # Query Input Box
    default_text = sample_selected if sample_selected else ""
    user_query = st.text_area(
        "Describe symptoms, condition, or clinical guideline query:", 
        value=default_text, 
        placeholder="e.g. Patient has blood pressure of 145/95 mmHg. When should pharmacological treatment begin?",
        height=100
    )
    
    col_submit, col_clear = st.columns([1, 5])
    with col_submit:
        submit_btn = st.button("🚀 Analyze Query", type="primary", use_container_width=True)
        
    if submit_btn and user_query.strip():
        with st.spinner("🔍 Searching vector database & generating grounded answer..."):
            try:
                vectordb = get_vector_db()
                if vectordb is None:
                    st.error("Vector database is not initialized. Please go to 'Document Management' tab to run ingestion.")
                else:
                    # Step 1: Retrieval
                    retrieved_results = retrieve(vectordb, user_query.strip())
                    
                    # Step 2: Generation
                    response = generate_grounded_answer(user_query.strip(), retrieved_results)
                    
                    st.markdown("---")
                    st.markdown("## 📋 Clinical Analysis Result")
                    
                    # Header Info (Confidence Badge)
                    confidence = response.get("confidence", "insufficient")
                    badge_html = get_confidence_badge_html(confidence)
                    st.markdown(f"**Grounding Status:** {badge_html}", unsafe_allow_html=True)
                    
                    # Recommendation Card
                    recommendation = response.get("recommendation", "No recommendation provided.")
                    st.markdown(f"""
                    <div class="recommendation-box">
                        <h4 style="margin-top: 0; color: #38bdf8;">🩺 Recommendation:</h4>
                        <div style="font-size: 1.05rem; line-height: 1.6; color: #f8fafc;">
                            {recommendation}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Evidence Excerpt Card
                    evidence = response.get("evidence", "")
                    if evidence:
                        st.markdown(f"""
                        <div class="evidence-box">
                            <h5 style="margin-top: 0; color: #c084fc;">📌 Direct Evidence Excerpt:</h5>
                            "{evidence}"
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Citations Accordion
                    citations = response.get("citations", [])
                    st.markdown("### 📚 Source Citations & References")
                    if citations:
                        for idx, cit in enumerate(citations, 1):
                            doc_name = cit.get("document", "Unknown Document")
                            sec = cit.get("section", "N/A")
                            page = cit.get("page", "?")
                            
                            st.markdown(f"""
                            <div class="citation-tag">
                                <b>[{idx}] Document:</b> {doc_name} &nbsp;|&nbsp; 
                                <b>Page:</b> {page} &nbsp;|&nbsp; 
                                <b>Section:</b> {sec}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No citations attached (Insufficient evidence or refusal response).")
                        
                    # Retrieved Chunks Accordion (Debugging/Inspection)
                    with st.expander("🔍 View Raw Retrieved Document Chunks"):
                        if retrieved_results:
                            for idx, (doc, score) in enumerate(retrieved_results, 1):
                                meta = doc.metadata
                                st.markdown(f"**Chunk #{idx}** | Similarity Score: `{score:.4f}` | Page: `{meta.get('page_number')}` | Chunk ID: `{meta.get('chunk_id')}`")
                                st.code(doc.page_content, language="markdown")
                        else:
                            st.write("No chunks retrieved.")
                            
            except Exception as e:
                st.error(f"An error occurred while processing the request: {e}")


# ==========================================
# TAB 2: DOCUMENT MANAGEMENT & INGESTION
# ==========================================
with tab_upload:
    st.markdown("### 📄 Clinical Guideline Document Manager")
    st.write("Upload official clinical guideline PDF files to index them into ChromaDB for retrieval.")
    
    uploaded_files = st.file_uploader(
        "Choose PDF Guideline Files", 
        type=["pdf"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        for file in uploaded_files:
            save_path = config.DATA_DIR / file.name
            with open(save_path, "wb") as f:
                f.write(file.getbuffer())
            st.success(f"Saved {file.name} to `./data/`")

    st.markdown("---")
    st.markdown("### ⚡ Re-Index Database")
    st.write("Run document chunking and vector embedding generation for all PDFs in `./data/`.")
    
    if st.button("🔨 Re-Build ChromaDB Index Now", type="primary"):
        with st.spinner("Processing PDFs, chunking, and embedding vectors..."):
            try:
                documents = load_pdfs(config.DATA_DIR)
                chunks = chunk_documents(documents)
                build_index(chunks)
                st.cache_resource.clear()
                st.success(f"Successfully indexed {len(chunks)} chunks from {len(documents)} pages!")
            except Exception as e:
                st.error(f"Ingestion failed: {e}")
                
    st.markdown("---")
    st.markdown("### 📂 Currently Stored PDFs in `./data/`")
    pdf_files = sorted(config.DATA_DIR.glob("*.pdf"))
    if pdf_files:
        for pdf in pdf_files:
            size_kb = pdf.stat().st_size / 1024
            st.markdown(f"- 📄 **{pdf.name}** ({size_kb:.1f} KB)")
    else:
        st.info("No PDF files currently stored in `./data/`.")


# ==========================================
# TAB 3: SYSTEM DIAGNOSTICS
# ==========================================
with tab_diagnostics:
    st.markdown("### 📊 System Diagnostics & Health")
    
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.markdown("#### 🗄️ Vector Store Status")
        st.write(f"- **Chroma Directory:** `{config.CHROMA_DIR}`")
        st.write(f"- **Collection Name:** `{config.COLLECTION_NAME}`")
        st.write(f"- **Chunk Size:** `{config.CHUNK_SIZE}` tokens")
        st.write(f"- **Chunk Overlap:** `{config.CHUNK_OVERLAP}` tokens")
        
        vectordb = get_vector_db()
        if vectordb:
            try:
                collection_count = vectordb._collection.count()
                st.metric("Total Indexed Chunks", collection_count)
            except Exception:
                st.metric("Total Indexed Chunks", "Active")
        else:
            st.metric("Total Indexed Chunks", "0 (Not initialized)")

    with col_d2:
        st.markdown("#### 🤖 LLM & Embedding Settings")
        st.write(f"- **Gemini API Key:** `{'Configured' if config.GEMINI_API_KEY else 'Missing'}`")
        st.write(f"- **Gemini Model:** `{config.GEMINI_MODEL}`")
        st.write(f"- **Embedding Provider:** `{config.EMBEDDING_PROVIDER}`")
        st.write(f"- **Local Embedding Model:** `{config.LOCAL_EMBEDDING_MODEL}`")
        st.write(f"- **Response Schema File:** `{config.BASE_DIR / 'schema' / 'response_schema.json'}`")

    st.markdown("---")
    st.markdown("#### 💡 Setup Instructions")
    st.markdown("""
    1. Place medical guideline PDF documents inside `./data/`.
    2. Click **Re-Build ChromaDB Index Now** in the Document Management tab or run `python ingest.py` in terminal.
    3. Ensure `GEMINI_API_KEY` is present in `.env`.
    4. Type your symptom or clinical question in the query tab.
    """)

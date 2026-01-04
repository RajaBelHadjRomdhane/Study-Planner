# front.py - Streamlit Application avec multi-pages
import streamlit as st
from streamlit_mermaid import st_mermaid
import uuid
import os
import re
from dotenv import load_dotenv
from backend.gemini_client import GeminiClient

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(env_path)

# Page configuration
st.set_page_config(
    page_title="AI Study Planner",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "gemini_client" not in st.session_state:
    try:
        st.session_state.gemini_client = GeminiClient()
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.settings = {
            "duration": "3 weeks",
            "current_level": "Beginner",
            "study_field": ""
        }
        st.session_state.db_initialized = st.session_state.gemini_client.use_database
        st.session_state.active_page = "🏠 Accueil"
        st.session_state.last_raw_response = None
    except Exception as e:
        st.error(f"Error initializing AI client: {str(e)}")
        st.stop()

# Show database status warning if needed
if not st.session_state.get("db_initialized", False) and not st.session_state.get("db_warning_shown", False):
    st.warning(
        "⚠️ **Database not connected**: Conversation history won't be saved between sessions. "
        "To enable persistence, set up your Supabase database by running the SQL script "
        "from `supabase_schema.sql` in your Supabase SQL Editor. See README.md for details."
    )
    st.session_state.db_warning_shown = True

# ==================== STYLES ====================
st.markdown("""
    <style>
    .toolbar {
        background-color: #f0f2f6;
        padding: 10px 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Ensure Mermaid diagrams are visible */
    .mermaid {
        background-color: #f8f9fa !important;
        padding: 15px !important;
        border-radius: 8px !important;
        border: 1px solid #dee2e6 !important;
    }
    
    /* Make sure text in Mermaid nodes is readable */
    .mermaid .nodeLabel {
        color: #000000 !important;
        font-weight: 500 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==================== NAVIGATION ====================
pages = {
    "🏠 Accueil": "home",
    "📊 Progress Tracking": "progress_tracking", 
}

# Initialize active_page if not exists
if "active_page" not in st.session_state:
    st.session_state.active_page = "🏠 Accueil"

col1, col2 = st.columns([3, 3])
with col2:
    toolbar_nav = st.container()
    with toolbar_nav:
        cols = st.columns(len(pages))
        for idx, (page_name, page_id) in enumerate(pages.items()):
            with cols[idx]:
                if st.button(page_name, key=f"toolbar_{page_id}", 
                           use_container_width=True,
                           type="primary" if st.session_state.active_page == page_name else "secondary"):
                    st.session_state.active_page = page_name
                    st.rerun()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("⚙️ Study Settings")
    st.markdown("---")
    
    study_field = st.text_input(
        "Study Field/Topic",
        value=st.session_state.settings.get("study_field", ""),
        placeholder="e.g., Python, Machine Learning, Java",
        help="Enter the subject you want to study"
    )
    
    current_level = st.selectbox(
        "Current Level",
        ["Beginner", "Intermediate", "Advanced"],
        index=["Beginner", "Intermediate", "Advanced"].index(
            st.session_state.settings.get("current_level", "Beginner")
        ),
        help="Select your current proficiency level"
    )
    
    duration = st.selectbox(
        "Study Duration",
        ["1 week", "2 weeks", "3 weeks", "1 month", "2 months", "3 months", "6 months", "Custom"],
        index=["1 week", "2 weeks", "3 weeks", "1 month", "2 months", "3 months", "6 months", "Custom"].index(
            st.session_state.settings.get("duration", "3 weeks")
        ) if st.session_state.settings.get("duration", "3 weeks") in ["1 week", "2 weeks", "3 weeks", "1 month", "2 months", "3 months", "6 months"] else 7,
        help="Select your desired study timeline"
    )
    
    if duration == "Custom":
        custom_duration = st.text_input(
            "Custom Duration",
            placeholder="e.g., 5 weeks, 10 days",
            help="Enter a custom duration"
        )
        if custom_duration:
            duration = custom_duration
    
    st.session_state.settings = {
        "duration": duration,
        "current_level": current_level,
        "study_field": study_field
    }
    
    
  
    
    if st.button("🔄 Reset Conversation", use_container_width=True, help="Reset conversation"):
        st.session_state.gemini_client.reset_conversation()
        st.session_state.last_raw_response = None
        st.session_state.messages = []
        st.rerun()

    if st.button("🔧 Render Mermaid Test", use_container_width=True, help="Render a simple test Mermaid diagram to debug rendering"):
        test_diagram = """graph TD
    A[Test Start] --> B[Test End]
    style A fill:#4d94ff
    style B fill:#33cc33"""
        display_message(test_diagram)
    
    st.markdown("---")
    st.caption("💡 **Tip:** Set your study preferences before asking for a plan!")

# ==================== UTILITY FUNCTIONS ====================

def extract_mermaid_diagrams(response_text):
    """Extract Mermaid diagrams from response text - FIXED VERSION"""
    diagrams = []

    if not response_text:
        return diagrams

    # 1) Explicit fenced mermaid blocks (```mermaid ... ```) - case-insensitive
    matches = re.findall(r'```\s*mermaid\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
    for m in matches:
        if m and m.strip():
            diagrams.append(m.strip())

    # 2) Generic fenced code blocks (```...``` or ~~~...~~~) that look like mermaid
    if not diagrams:
        fenced = re.findall(r'```(?:\w+)?\s*(.*?)\s*```', response_text, re.DOTALL)
        fenced += re.findall(r'~~~\s*(.*?)\s*~~~', response_text, re.DOTALL)
        for code in fenced:
            c = code.strip()
            if not c:
                continue
            low = c.lower()
            if ('flowchart' in low or 'graph' in low or 'classdef' in low
                    or '-->' in c or ('[' in c and ']' in c)):
                diagrams.append(c)

    # 3) Inline/raw mermaid blocks (no fences) - look for blocks starting with flowchart/graph
    if not diagrams:
        inline = re.findall(r'(?:(?:^|\n)(?:flowchart|graph)[\s\S]*?)(?=\n{2,}|$)', response_text, re.IGNORECASE)
        for block in inline:
            b = block.strip()
            if b:
                diagrams.append(b)

    return diagrams

def validate_and_clean_mermaid(diagram_code):
    """Clean and validate Mermaid diagram code before rendering."""
    if not diagram_code:
        return None
    # Strip any surrounding fences/backticks
    cleaned = re.sub(r'^```\w*|```$', '', diagram_code).strip()

    # Replace common smart-quotes and non-breaking spaces
    cleaned = cleaned.replace('\u201c', '"').replace('\u201d', '"')
    cleaned = cleaned.replace('\u2018', "'").replace('\u2019', "'")
    cleaned = cleaned.replace('\u00A0', ' ')

    # Remove leading blockquote markers and trim each line
    lines = [ln.lstrip('> ').rstrip() for ln in cleaned.split('\n')]
    lines = [ln for ln in lines if ln and not ln.startswith('%% mermaid')]
    cleaned = '\n'.join(lines).strip()

    low = cleaned.lower()

    # Ensure it starts with a recognized mermaid block type; if not, try to extract or prepend
    if not (low.startswith('flowchart') or low.startswith('graph') or low.startswith('sequence') or low.startswith('gantt')):
        if 'flowchart' in low:
            idx = low.find('flowchart')
            cleaned = cleaned[idx:]
        elif 'graph' in low:
            idx = low.find('graph')
            cleaned = cleaned[idx:]
        else:
            cleaned = f"flowchart TD\n{cleaned}"

    # Add default class definitions when ':::' used but no classDef present
    if 'classdef' not in low and ':::' in cleaned:
        color_defs = (
            "classDef foundation fill:#4d94ff,color:#000,stroke:#333,stroke-width:2px\n"
            "classDef core fill:#33cc33,color:#000,stroke:#333,stroke-width:2px\n"
            "classDef practice fill:#ff9900,color:#000,stroke:#333,stroke-width:2px\n"
            "classDef project fill:#9933ff,color:#fff,stroke:#333,stroke-width:2px\n"
            "classDef review fill:#ff3333,color:#fff,stroke:#333,stroke-width:2px"
        )
        parts = cleaned.split('\n')
        if len(parts) > 0:
            parts.insert(1, color_defs)
            cleaned = '\n'.join(parts)

    return cleaned

def remove_mermaid_blocks(response_text):
    """Remove all Mermaid code blocks from response text."""
    # First remove explicit mermaid blocks
    pattern1 = r'```mermaid\s*.*?\s*```'
    cleaned = re.sub(pattern1, '', response_text, flags=re.DOTALL)
    
    # Then remove any remaining code blocks that might be mermaid
    pattern2 = r'```\s*.*?\s*```'
    cleaned = re.sub(pattern2, '', cleaned, flags=re.DOTALL)
    
    return cleaned.strip()

def display_message(message_content):
    """Display a single message with Mermaid diagram handling - FIXED VERSION"""
    # Store for debugging
    st.session_state.last_raw_response = message_content
    
    # Extract diagrams
    diagrams = extract_mermaid_diagrams(message_content)
    
    # Display text content without diagrams
    text_content = remove_mermaid_blocks(message_content)
    if text_content:
        st.markdown(text_content)
    
    # Display diagrams if found
    if diagrams:
        st.markdown("---")
        st.subheader("📊 Study Roadmap Diagram")
        
        # Take the first diagram
        diagram_raw = diagrams[0]
        diagram_clean = validate_and_clean_mermaid(diagram_raw)
        
        if not diagram_clean:
            st.error("❌ Could not parse Mermaid diagram")
            st.code(diagram_raw[:500], language="text")
        else:
                        try:
                                # Prefer rendering via an HTML component using the Mermaid CDN for reliability
                                import time
                                unique_key = f"mermaid_{int(time.time() * 1000)}"
                                import streamlit.components.v1 as components

                                # Use a wrapper div id so multiple diagrams don't clash
                                wrapper_id = f"{unique_key}_wrap"
                                html = f"""<!doctype html>
<html><head><meta charset=\"utf-8\"> 
    <script src=\"https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js\"></script>
    <style>.mermaid{{background:transparent}}</style>
</head>
<body>
    <div id=\"{wrapper_id}\"> <div class=\"mermaid\">{diagram_clean}</div> </div>
    <script>
        try {{
            mermaid.initialize({{ startOnLoad: false, securityLevel: 'loose' }});
            mermaid.init(undefined, document.querySelectorAll('#{wrapper_id} .mermaid'));
        }} catch(err) {{
            console.error('mermaid init error', err);
        }}
    </script>
</body></html>"""

                                components.html(html, height=420, scrolling=True)
                                st.success("✅ Diagram displayed")

                                # Show the code
                                with st.expander("📝 View Diagram Code"):
                                        st.code(diagram_clean, language="mermaid")

                        except Exception as e:
                                st.error(f"❌ Mermaid rendering error: {str(e)}")

                                # Show debug info
                                with st.expander("🔍 Debug: Raw Diagram Code"):
                                        st.code(diagram_clean, language="mermaid")

                                # As a last resort, attempt st_mermaid if available
                                try:
                                        st.info("Attempting fallback with `st_mermaid` component...")
                                        st_mermaid(diagram_clean, key=unique_key, height=400)
                                        st.success("✅ Fallback st_mermaid render succeeded")
                                except Exception as e2:
                                        st.error(f"❌ Fallback render failed: {str(e2)}")
        
        st.markdown("---")

# ==================== HOME PAGE ====================
if st.session_state.active_page == "🏠 Accueil":
    st.title("🏠 Home - AI Study Planner")
    st.markdown("Your intelligent study planning assistant powered by Gemini 2.5 Flash")
    
    # Quick stats
    if st.session_state.messages:
        user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in st.session_state.messages if msg["role"] == "assistant"]
        diagrams_count = sum(1 for msg in assistant_messages if extract_mermaid_diagrams(msg["content"]))
        
        with st.container():
            cols = st.columns(4)
            with cols[0]:
                st.metric("Conversations", "1")
            with cols[1]:
                st.metric("Your Messages", len(user_messages))
            with cols[2]:
                st.metric("Diagrams", diagrams_count)
            with cols[3]:
                status = "Active" if st.session_state.gemini_client else "Inactive"
                st.metric("Status", status)
    
    # Display chat history
    chat_container = st.container()
    for message in st.session_state.messages:
        with chat_container:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    display_message(message["content"])
                else:
                    st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask for a study plan or ask questions about your learning journey..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Show user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    response = st.session_state.gemini_client.chat(
                        prompt,
                        session_id=st.session_state.session_id,
                        user_settings=st.session_state.settings
                    )
                    
                    # Store the raw response
                    st.session_state.last_raw_response = response
                    
                    # Display the response
                    display_message(response)
                    
                    # Add to messages
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # Save roadmap if valid diagram and DB enabled
                    diagrams = extract_mermaid_diagrams(response)
                    if diagrams and st.session_state.gemini_client.use_database:
                        try:
                            title = f"Roadmap: {prompt[:50]}..." if len(prompt) > 50 else f"Roadmap: {prompt}"
                            st.session_state.gemini_client.save_roadmap(title, diagrams[0])
                            st.toast("✅ Roadmap saved to database!")
                        except Exception as e:
                            st.warning(f"Could not save roadmap: {e}")
                            
                except Exception as e:
                    error_msg = f"Error generating response: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

# ==================== PROGRESS TRACKING PAGE ====================
elif st.session_state.active_page == "📊 Progress Tracking":
    st.title("📊 Progress Tracking")
    st.markdown("Visualize your study progress")
    
    if not st.session_state.get("db_initialized", False):
        st.warning("⚠️ Database not connected. Progress tracking requires database setup.")
        st.info("Please set up Supabase database to enable progress tracking features.")
    else:
        try:
            roadmaps = st.session_state.gemini_client.get_roadmaps()
            
            if roadmaps:
                roadmap_options = {rm["id"]: rm["title"] for rm in roadmaps}
                selected_roadmap_id = st.selectbox(
                    "Select a roadmap to track progress:",
                    options=list(roadmap_options.keys()),
                    format_func=lambda x: roadmap_options[x],
                    key="roadmap_selector"
                )
                
                if selected_roadmap_id:
                    progress_data = st.session_state.gemini_client.get_roadmap_progress(selected_roadmap_id)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Items", progress_data["total_items"])
                    with col2:
                        st.metric("Completed", progress_data["completed_items"])
                    with col3:
                        progress_pct = progress_data.get("progress_percentage", 0)
                        st.metric("Progress", f"{progress_pct:.1f}%")
                    
                    st.progress(progress_pct / 100 if progress_pct else 0)
                    
                    st.subheader("📝 Roadmap Items")
                    for item in progress_data["items"]:
                        completed = item.get("completed", False)
                        item_title = item.get("title", "Unknown")
                        
                        new_completed = st.checkbox(
                            item_title,
                            value=completed,
                            key=f"item_{item['id']}"
                        )
                        
                        if new_completed != completed:
                            success = st.session_state.gemini_client.update_item_progress(item["id"], new_completed)
                            if success:
                                st.success(f"✅ Updated: {item_title}")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to update: {item_title}")
            else:
                st.info("📚 No roadmaps found. Generate a study plan to start tracking progress!")
                st.markdown("""
                ### How to create your first roadmap:
                1. Go to **Home** page
                2. Ask: "Create an Angular study plan with a mermaid flowchart diagram"
                3. The AI will generate a Mermaid diagram
                4. It will be automatically saved for tracking
                """)
                
        except Exception as e:
            st.error(f"Error loading progress tracker: {e}")
            st.info("Make sure your database is properly configured and tables are created.")


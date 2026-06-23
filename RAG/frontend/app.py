import streamlit as st
import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
USER_ID = "default_user" # Simulated user for session persistence

st.set_page_config(page_title="AI Academic Assistant", layout="wide", page_icon="📚")

st.markdown("""
<style>
    /* Clean layout enhancements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding-top: 2rem;
        padding-bottom: 10rem;
    }
    
    /* Smooth transitions and chat UX */
    .stChatMessage {
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    button {
        transition: background-color 0.3s ease, border-color 0.3s ease, transform 0.1s ease !important;
    }
    button:active {
        transform: scale(0.98);
    }
</style>
""", unsafe_allow_html=True)

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

def fetch_sessions():
    try:
        response = requests.get(f"{BACKEND_URL}/api/chat/sessions/{USER_ID}")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch sessions: {e}")
    return []

def load_session_history(session_id):
    try:
        response = requests.get(f"{BACKEND_URL}/api/chat/history/{session_id}")
        if response.status_code == 200:
            history = response.json()
            st.session_state.messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]
            st.session_state.session_id = session_id
    except Exception as e:
        st.error(f"Failed to load history: {e}")

# --- Sidebar UI ---
st.sidebar.title("📚 AI Academic Assistant")
st.sidebar.subheader("1. Index Document")
uploaded_file = st.sidebar.file_uploader("Upload PDF or DOCX", type=["pdf", "docx", "txt"])
if st.sidebar.button("Upload & Index"):
    if uploaded_file is not None:
        with st.spinner("Indexing document (extracting, chunking, embedding)..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {"user_id": USER_ID}
            try:
                res = requests.post(f"{BACKEND_URL}/api/documents/upload", files=files, data=data)
                if res.status_code == 200:
                    st.sidebar.success(f"Successfully indexed {uploaded_file.name}!")
                else:
                    st.sidebar.error("Failed to upload document.")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
    else:
        st.sidebar.warning("Please select a file.")

st.sidebar.markdown("---")
st.sidebar.subheader("2. Chat History")
sessions = fetch_sessions()
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("➕ New", use_container_width=True, type="primary" if not st.session_state.session_id else "secondary"):
        st.session_state.session_id = None
        st.session_state.messages = []
with col2:
    if st.button("🧹 Clear", use_container_width=True):
        st.session_state.messages = []

for idx, session in enumerate(sessions):
    is_active = (session['id'] == st.session_state.session_id)
    btn_type = "primary" if is_active else "secondary"
    
    date_str = session['created_at'][:10]
    if st.sidebar.button(f"💬 {date_str} [{session['id'][:4]}]", key=f"sess_{session['id']}", use_container_width=True, type=btn_type):
        load_session_history(session['id'])

st.sidebar.markdown("---")
st.sidebar.info("Features:\n- Fast Groq LLM Inference\n- Persistent memory across chats\n- FAISS vector search")

# --- Main UI ---
st.title("📚 Chat with your Documents")
if st.session_state.session_id:
    st.caption(f"Active Session: `{st.session_state.session_id}` • *Context Memory Enabled*")
else:
    st.caption("✨ Start a new conversation or load a session from the sidebar to continue your research.")

# Welcome placeholder when empty
if not st.session_state.messages:
    st.markdown("<br><br><h3 style='text-align: center; color: #888;'>How can I assist you with your reading today?</h3>", unsafe_allow_html=True)

def render_tts_button(msg_index, text_content, auto_play=False):
    import json
    import streamlit.components.v1 as components
    content_json = json.dumps(text_content)
    auto_play_js = "if (!window.hasAutoPlayed) { window.hasAutoPlayed = true; btn.click(); }" if auto_play else ""
    
    html = f"""
    <style>
        body {{ font-family: "Source Sans Pro", sans-serif; margin: 0; padding: 0; background-color: transparent; }}
        .play-btn {{ background: none; border: none; color: #ccc; cursor: pointer; font-size: 14px; display: flex; align-items: center; gap: 5px; }}
        .play-btn:hover {{ color: #fff; }}
    </style>
    
    <div id="tts-container-{msg_index}" style="margin-top: 5px;">
        <button class="play-btn" id="tts-btn-{msg_index}">🔈 Read Aloud</button>
    </div>
    
    <script>
        const btn = document.getElementById("tts-btn-{msg_index}");
        let audio = null;
        let timestamps = [];
        
        btn.onclick = async () => {{
            const parentDoc = window.parent.document;
            
            if (audio) {{
                if (audio.paused) {{
                    if (parentDoc.currentTTS && parentDoc.currentTTS.audio !== audio) {{
                        parentDoc.currentTTS.audio.pause();
                        if (parentDoc.currentTTS.btn) parentDoc.currentTTS.btn.innerHTML = '🔈 Read Aloud';
                    }}
                    audio.play();
                    btn.innerHTML = '⏸️ Pause';
                    parentDoc.currentTTS = {{ audio: audio, btn: btn }};
                }} else {{
                    audio.pause();
                    btn.innerHTML = '🔈 Read Aloud';
                }}
                return;
            }}
            
            // First time click - generate audio!
            btn.innerHTML = '⏳ Loading...';
            btn.disabled = true;
            
            try {{
                const res = await fetch('{BACKEND_URL}/api/chat/synthesize', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ text: {content_json} }})
                }});
                
                if (res.ok) {{
                    const data = await res.json();
                    const audioUrl = '{BACKEND_URL}' + data.audio_url;
                    timestamps = data.timestamps;
                    
                    audio = new Audio(audioUrl);
                    
                    // DOM walker logic targeting specific message index!
                    const parentDoc = window.parent.document;
                    const anchor = parentDoc.getElementById('msg-{msg_index}');
                    if (anchor) {{
                        const chatMessageContainer = anchor.closest('div[data-testid="stChatMessage"]');
                        if (chatMessageContainer) {{
                            const markdownContainer = chatMessageContainer.querySelector('div[data-testid="stMarkdownContainer"]');
                            if (markdownContainer && !markdownContainer.dataset.processed) {{
                                const walker = parentDoc.createTreeWalker(markdownContainer, NodeFilter.SHOW_TEXT, null, false);
                                const textNodes = [];
                                let node;
                                while(node = walker.nextNode()) {{
                                    if(node.nodeValue.trim() !== '') {{
                                        textNodes.push(node);
                                    }}
                                }}
                                
                                let globalWordIndex = 0;
                                textNodes.forEach(textNode => {{
                                    const text = textNode.nodeValue;
                                    const words = text.split(/(\\s+)/);
                                    const fragment = parentDoc.createDocumentFragment();
                                    
                                    words.forEach(word => {{
                                        if (word.trim() === '' || !/[A-Za-z0-9]/.test(word)) {{
                                            fragment.appendChild(parentDoc.createTextNode(word));
                                        }} else {{
                                            const span = parentDoc.createElement('span');
                                            span.innerText = word;
                                            span.id = 'ts-word-{msg_index}-' + globalWordIndex;
                                            span.style.transition = 'background-color 0.1s, color 0.1s';
                                            span.style.borderRadius = '2px';
                                            fragment.appendChild(span);
                                            globalWordIndex++;
                                        }}
                                    }});
                                    textNode.parentNode.replaceChild(fragment, textNode);
                                }});
                                markdownContainer.dataset.processed = "true";
                            }}
                            
                            // Audio highlight sync
                            audio.addEventListener('timeupdate', () => {{
                                const currentTime = audio.currentTime;
                                timestamps.forEach((item, index) => {{
                                    const el = parentDoc.getElementById('ts-word-{msg_index}-' + index);
                                    if (el) {{
                                        if (currentTime >= item.start && currentTime <= item.end) {{
                                            el.style.backgroundColor = '#ffd54f';
                                            el.style.color = '#000';
                                        }} else if (currentTime > item.end) {{
                                            el.style.backgroundColor = 'transparent';
                                            el.style.color = '#87cefa'; // Light blue color
                                        }} else {{
                                            el.style.backgroundColor = 'transparent';
                                            el.style.color = 'inherit';
                                        }}
                                    }}
                                }});
                            }});
                        }}
                    }}
                    
                    audio.onended = () => {{ btn.innerHTML = '🔈 Read Aloud'; }};
                    
                    if (parentDoc.currentTTS && parentDoc.currentTTS.audio !== audio) {{
                        parentDoc.currentTTS.audio.pause();
                        if (parentDoc.currentTTS.btn) parentDoc.currentTTS.btn.innerHTML = '🔈 Read Aloud';
                    }}
                    
                    btn.innerHTML = '⏸️ Pause';
                    btn.disabled = false;
                    audio.play();
                    
                    parentDoc.currentTTS = {{ audio: audio, btn: btn }};
                }} else {{
                    btn.innerHTML = '❌ Error';
                    btn.disabled = false;
                }}
            }} catch(e) {{
                btn.innerHTML = '❌ Error';
                btn.disabled = false;
            }}
        }};
        
        {auto_play_js}
    </script>
    """
    components.html(html, height=35, scrolling=False)

# Render existing messages
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(f'<div id="msg-{i}"></div>\n\n' + message["content"], unsafe_allow_html=True)
        if message["role"] == "assistant":
            render_tts_button(i, message["content"])

# Inject global CSS for mic styling
st.markdown("""
<style>
iframe[title*="mic_recorder"] {
    width: 35px !important;
    height: 35px !important;
    background: transparent !important;
    border: none !important;
    z-index: 999999;
}
</style>
""", unsafe_allow_html=True)

# Chat input & Mic
prompt = st.chat_input("Ask a question about your documents...")
from streamlit_mic_recorder import mic_recorder
audio_bytes = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic_recorder", format="wav")

# JS hack to perfectly move the mic iframe directly inside the chat input pill and inject the sleek SVG
import streamlit.components.v1 as components
components.html("""
<script>
    const parentDoc = window.parent.document;

    // 1. Relocate the iframe using FIXED positioning glued to the Send button
    setInterval(() => {
        const mic = parentDoc.querySelector('iframe[title*="mic_recorder"]');
        if (!mic) return;
        
        // Find the chat input by its specific placeholder text, ignoring whether it's an input or textarea
        const chatInput = parentDoc.querySelector('[aria-label*="Ask a question"], [placeholder*="Ask a question"]');
        
        if (chatInput) {
            // Traverse up a few levels to find the pill container that holds the Send button
            let current = chatInput;
            let sendBtn = null;
            for(let i=0; i<4; i++) {
                if (current.parentElement) {
                    current = current.parentElement;
                    const btn = current.querySelector('button');
                    if (btn) {
                        sendBtn = btn;
                        break;
                    }
                }
            }
            
            if (sendBtn) {
                // DO NOT move the iframe in the DOM! Moving an iframe causes the browser to reload it, breaking the Streamlit component!
                // Instead, just break it out of the layout flow visually using fixed positioning.
                mic.style.position = 'fixed';
                mic.style.zIndex = '999999';
                
                // Add padding to input so text doesn't overlap the mic
                chatInput.parentElement.style.paddingRight = '45px';
                
                // Constantly update position to stay glued exactly 40 pixels left of the send button!
                const btnRect = sendBtn.getBoundingClientRect();
                mic.style.left = (btnRect.left - 40) + 'px'; 
                mic.style.top = (btnRect.top + (btnRect.height / 2) - 17.5) + 'px'; // Center vertically
            }
        }
    }, 50);

    // 2. Inject sleek SVG into the iframe button
    setInterval(() => {
        try {
            const mic = parentDoc.querySelector('iframe[title*="mic_recorder"]');
            if (!mic) return;
            const micDoc = mic.contentDocument || mic.contentWindow.document;
            if (!micDoc) return;
            
            // Make the iframe's internal body completely transparent
            if (micDoc.body) {
                micDoc.body.style.background = 'transparent';
                micDoc.body.style.backgroundColor = 'transparent';
            }
            
            const btn = micDoc.querySelector('button');
            if (!btn) return;
            
            if (btn.innerText.includes('🎤')) {
                btn.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-top:2px;"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg>`;
                btn.style.background = 'transparent';
                btn.style.border = 'none';
                btn.style.boxShadow = 'none';
                btn.style.padding = '0';
            } else if (btn.innerText.includes('⏹️')) {
                btn.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FF4B4B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-top:2px;"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect></svg>`;
                btn.style.background = 'transparent';
                btn.style.border = 'none';
                btn.style.boxShadow = 'none';
                btn.style.padding = '0';
            }
        } catch(e) {}
    }, 100);
</script>
""", height=0)

if audio_bytes and not prompt:
    audio_id = audio_bytes.get("id")
    if audio_id != st.session_state.get("last_processed_audio_id"):
        st.session_state["last_processed_audio_id"] = audio_id
        with st.spinner("Transcribing voice..."):
            try:
                res = requests.post(f"{BACKEND_URL}/api/chat/audio_transcribe", files={"file": ("audio.wav", audio_bytes["bytes"], "audio/wav")})
                if res.status_code == 200:
                    transcribed_text = res.json().get("text", "").strip()
                    if transcribed_text.startswith("[ERROR]"):
                        st.error(transcribed_text)
                    elif transcribed_text:
                        prompt = transcribed_text
                    else:
                        st.warning("No voice detected. Please ensure your microphone is working and speak clearly.")
                else:
                    st.error(f"STT Server Error: {res.status_code} - {res.text}")
            except Exception as e:
                st.error(f"Failed to transcribe: {e}")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Generating response..."):
            payload = {
                "user_id": USER_ID,
                "session_id": st.session_state.session_id,
                "message": prompt
            }
            try:
                res = requests.post(f"{BACKEND_URL}/api/chat/", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    response_text = data.get("text_response", "Error parsing response.")
                    tts_text = data.get("tts_text", "")
                    metadata = data.get("metadata", {})
                    
                    st.session_state.session_id = data.get("session_id")
                    
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    msg_index = len(st.session_state.messages) - 1
                    
                    message_placeholder.markdown(f'<div id="msg-{msg_index}"></div>\n\n' + response_text, unsafe_allow_html=True)
                    
                    # Call our unified TTS function to auto-play
                    render_tts_button(msg_index, response_text, auto_play=False)
                else:
                    message_placeholder.error(f"API Error: {res.text}")
            except Exception as e:
                message_placeholder.error(f"Connection Error: Is the backend running? ({e})")

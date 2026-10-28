"""
app.py - TechXfluence AI chatbot (Streamlit user interface).

Run with:   streamlit run app.py

RAG flow used here:
    question -> Retriever.search() -> best text chunks -> Ollama (Llama 3.2) -> answer + sources
"""

from __future__ import annotations

import html

import streamlit as st

import ollama_llm
import rag_engine

st.set_page_config(page_title="TechXfluence AI", page_icon="⚡", layout="centered")

SUGGESTIONS = [
    ("🛠️ Services", "What services does TechXfluence offer?"),
    ("🎟️ Events", "What types of events and workshops does TechXfluence run?"),
    ("💎 Membership", "What are the membership plans and their benefits?"),
    ("🚀 Host event", "How can I host an event on TechXfluence?"),
    ("💼 Careers", "What job roles are open at TechXfluence?"),
    ("✉️ Contact", "How can I contact TechXfluence?"),
]

# ----------------------------------------------------------------------------
# Custom CSS - dark navy, cyan + purple accents
# ----------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap');
:root { --navy:#0a1128; --navy2:#101a3a; --card:#131f45; --cyan:#22d3ee; --purple:#a78bfa; --text:#e6ecff; --muted:#93a0c8; }
html, body, [class*="css"], .stApp { font-family:'Inter',sans-serif; color:var(--text); }
.stApp { background: radial-gradient(1200px 600px at 10% -10%, #1b2a6b55, transparent),
                     radial-gradient(900px 500px at 100% 0%, #6d3fd244, transparent), var(--navy); }
header[data-testid="stHeader"] { background:transparent; }
.block-container { padding-top:1.5rem; max-width:860px; }

.brand { display:flex; align-items:center; gap:14px; padding:18px 20px; border-radius:18px;
         background:linear-gradient(135deg,#132155,#1d1650); border:1px solid #2b3b7a; margin-bottom:14px; }
.brand .logo { width:48px; height:48px; border-radius:14px; display:grid; place-items:center; font-size:26px;
               background:linear-gradient(135deg,var(--cyan),var(--purple)); box-shadow:0 0 24px #22d3ee55; }
.brand h1 { font-family:'Space Grotesk',sans-serif; font-size:1.7rem; margin:0; line-height:1.1; color:#fff; }
.brand h1 span { background:linear-gradient(90deg,var(--cyan),var(--purple)); -webkit-background-clip:text; color:transparent; }
.brand p { margin:2px 0 0; color:var(--muted); font-size:.9rem; }

[data-testid="stChatMessage"] { background:var(--card); border:1px solid #243468; border-radius:16px; padding:14px 16px; }
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { line-height:1.6; font-size:.98rem; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background:linear-gradient(135deg,#1c2a63,#2a1f66); border-color:#4a3fa0; }

.stButton > button, .stButton > button p { color:var(--text) !important; }
.stButton > button { background:var(--navy2); border:1px solid #2f4189; border-radius:999px;
                     padding:.45rem .9rem; font-size:.88rem; transition:all .15s; width:100%; }
.stButton > button:hover { border-color:var(--cyan); color:var(--cyan); box-shadow:0 0 14px #22d3ee33; transform:translateY(-1px); }

.src { display:inline-block; margin:4px 6px 0 0; padding:4px 10px; border-radius:999px; font-size:.78rem;
       background:#0e1a42; border:1px solid #2f4189; color:var(--cyan) !important; text-decoration:none; }
.src:hover { border-color:var(--purple); color:var(--purple) !important; }
.src-label { color:var(--muted); font-size:.78rem; margin-top:10px; }

[data-testid="stSidebar"] { background:#080e22; border-right:1px solid #1d2a5c; }
.step { display:flex; gap:10px; align-items:flex-start; margin:8px 0; font-size:.88rem; color:var(--text); }
.step b { min-width:24px; height:24px; border-radius:50%; display:grid; place-items:center; font-size:.75rem;
          background:linear-gradient(135deg,var(--cyan),var(--purple)); color:#07102a; }
.pill { display:inline-block; padding:3px 10px; border-radius:999px; font-size:.78rem; font-weight:600; }
.ok { background:#06402f; color:#4ade80; } .bad { background:#4a1120; color:#fb7185; } .warn { background:#4a3a0a; color:#fbbf24; }

[data-testid="stChatInput"] { border-radius:14px; background:var(--navy2); border:1px solid #2f4189; }
[data-testid="stChatInput"] textarea { color:var(--text) !important; background:transparent; }
[data-testid="stBottom"], [data-testid="stBottom"] > div { background:var(--navy) !important; }
.stApp, .stApp p, .stApp li, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, [data-testid="stMarkdownContainer"] { color:var(--text); }
.stCaption, [data-testid="stCaptionContainer"] { color:var(--muted) !important; }
[data-testid="stSidebar"] * { color:var(--text); }
.brand h1 span { color:transparent !important; }
.pill.ok { color:#4ade80 !important; } .pill.bad { color:#fb7185 !important; } .pill.warn { color:#fbbf24 !important; }
.step b { color:#07102a !important; }
.src, .src * { color:var(--cyan) !important; }
.footer { text-align:center; color:var(--muted); font-size:.75rem; margin-top:18px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Cached resources
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_retriever() -> rag_engine.Retriever:
    return rag_engine.Retriever()


def reload_knowledge():
    get_retriever.clear()


retriever = get_retriever()

# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None


def sources_html(sources: list[dict]) -> str:
    parts = ['<div class="src-label">Sources used</div>']
    for s in sources:
        label = html.escape(f'{s["title"]} · {s["file"]}')
        if s["source"].startswith("http"):
            parts.append(f'<a class="src" href="{html.escape(s["source"])}" target="_blank">🔗 {label}</a>')
        else:
            parts.append(f'<span class="src">📄 {label}</span>')
    return "".join(parts)


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
status = ollama_llm.get_status()
with st.sidebar:
    st.markdown("### ⚡ TechXfluence AI")
    st.caption("Local RAG chatbot · no API key needed")

    st.markdown("**Local AI model status**")
    if not status["running"]:
        st.markdown('<span class="pill bad">● Ollama not running</span>', unsafe_allow_html=True)
        st.caption("Start the Ollama app, then refresh this page.")
    elif not status["model_ready"]:
        st.markdown('<span class="pill warn">● Model not downloaded</span>', unsafe_allow_html=True)
        st.code(f"ollama pull {status['model']}", language="bash")
    else:
        st.markdown(f'<span class="pill ok">● {status["model"]} ready</span>', unsafe_allow_html=True)

    st.markdown("**Knowledge base**")
    if retriever.ready:
        files = sorted({c.filename for c in retriever.chunks})
        st.caption(f"{len(retriever.chunks)} chunks from {len(files)} file(s): " + ", ".join(files))
    else:
        st.error("No knowledge found in the data/ folder.")

    st.markdown("**RAG pipeline**")
    st.markdown(
        """
<div class="step"><b>1</b><span>You ask a question</span></div>
<div class="step"><b>2</b><span>Search the knowledge base (BM25)</span></div>
<div class="step"><b>3</b><span>Retrieve the most relevant sections</span></div>
<div class="step"><b>4</b><span>Send context + question to Llama 3.2 (local)</span></div>
<div class="step"><b>5</b><span>Answer is generated from that context only</span></div>
<div class="step"><b>6</b><span>Answer and sources are shown</span></div>
""",
        unsafe_allow_html=True,
    )
    st.divider()
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.session_state.pending = None
        st.rerun()
    if st.button("🔄 Reload knowledge"):
        reload_knowledge()
        st.rerun()

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.markdown(
    """
<div class="brand">
  <div class="logo">⚡</div>
  <div><h1>TechXfluence <span>AI</span></h1>
  <p>Your guide to the TechXfluence community — services, events, membership &amp; careers</p></div>
</div>
""",
    unsafe_allow_html=True,
)

# Welcome message + suggested questions (shown until the first question)
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="⚡"):
        st.markdown(rag_engine.WELCOME_MESSAGE)
    st.caption("Try one of these:")
    cols = st.columns(3)
    for i, (label, question) in enumerate(SUGGESTIONS):
        if cols[i % 3].button(label, key=f"sg{i}", help=question):
            st.session_state.pending = question
            st.rerun()

# ----------------------------------------------------------------------------
# Chat history
# ----------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="⚡" if msg["role"] == "assistant" else "🧑"):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.markdown(sources_html(msg["sources"]), unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Handle a new question
# ----------------------------------------------------------------------------
typed = st.chat_input("Ask about TechXfluence services, events, membership, careers...")
question = typed or st.session_state.pending
st.session_state.pending = None


def retrieval_query(q: str) -> str:
    """Short follow-ups ("and the price?") borrow words from the previous question."""
    words = [w for w in q.lower().split() if w not in rag_engine.STOPWORDS]
    prev = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
    return f"{prev[-1]} {q}" if len(words) <= 2 and prev else q


if question:
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="⚡"):
        answer, sources = "", []

        if rag_engine.is_greeting(question):
            answer = rag_engine.WELCOME_MESSAGE
            st.markdown(answer)
        elif not retriever.ready:
            answer = "The knowledge base is empty. Add content to the data/ folder (see README_Tanglish.txt)."
            st.error(answer)
        else:
            retrieved = retriever.search(retrieval_query(question))
            if not retrieved:
                # Nothing relevant found -> do NOT ask the LLM (prevents made-up answers).
                answer = rag_engine.NOT_FOUND_MESSAGE
                st.markdown(answer)
            else:
                prompt = rag_engine.build_prompt(question, retrieved)
                try:
                    with st.spinner("TechXfluence AI is thinking..."):
                        stream = ollama_llm.stream_answer(prompt, rag_engine.SYSTEM_PROMPT, history)
                        first = next(stream, "")  # spinner stays until the first token arrives

                    def chained():
                        yield first
                        yield from stream

                    answer = st.write_stream(chained())
                    if rag_engine.is_not_found(answer):
                        answer = rag_engine.NOT_FOUND_MESSAGE
                    else:
                        sources = rag_engine.unique_sources(retrieved)
                        st.markdown(sources_html(sources), unsafe_allow_html=True)
                except ollama_llm.OllamaError as exc:
                    answer = f"⚠️ {exc}"
                    st.warning(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})

st.markdown(
    '<div class="footer">TechXfluence AI answers only from the saved TechXfluence knowledge base. '
    "Verify prices, dates and openings on the official website.</div>",
    unsafe_allow_html=True,
)

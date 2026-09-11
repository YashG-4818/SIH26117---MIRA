"""
app.py — Streamlit UI for the Sovereign AI Workbench.

Deliberately thin. Every decision about what the assistant can do, how tool
calls flow, and what needs a human's approval lives in agent.py; this file
only renders it. If you find yourself writing "if tool == X" logic in here,
that logic belongs in agent.py instead.

Two things worth understanding before touching this file:

1. Streamlit reruns this whole script top to bottom on every click. State
   that must survive a rerun - the Agent, the chat history, the last tool
   trace - lives in st.session_state, not in a plain variable.

2. The approval gate (agent.py's REQUIRE_APPROVAL tools) is rendered as a
   literal stop: while agent.pending is set, the chat input is hidden and
   only Approve/Reject buttons are shown. Nothing the model asked for runs
   until one of those buttons is clicked. That pause is real, not simulated -
   worth saying out loud to judges.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import config
from core import audit, kb, llm, netguard, outputs, sandbox
import agent as agent_mod

st.set_page_config(page_title=config.APP_NAME, page_icon="🛢️", layout="wide")

# The air-gap guard patches the socket layer of THIS process. It does nothing
# until install() is called - so this has to run before anything else touches
# the network, and it has to run every time the script starts. install() is
# idempotent (safe to call again on a Streamlit rerun) and cheap, so calling
# it unconditionally at import time is correct and simpler than trying to
# gate it behind session_state.
netguard.install()


# ---------------------------------------------------------------------------
# Look and feel
# ---------------------------------------------------------------------------
# This is styling only - it changes nothing about how the app behaves. Colours
# come from .streamlit/config.toml (the theme block); this CSS block handles
# the things Streamlit's theme system doesn't expose: the top banner, status
# pills, tab styling, and tightening up the default spacing so the app reads
# as a product rather than a prototype notebook.
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1.2rem; max-width: 1200px;}

    .sih-banner {
        display: flex; align-items: center; justify-content: space-between;
        padding: 1.1rem 1.6rem; margin-bottom: 1.4rem; border-radius: 10px;
        background: linear-gradient(135deg, #0B1F2E 0%, #123449 100%);
        color: #F2F6F8;
    }
    .sih-banner h1 {
        font-size: 1.35rem; margin: 0; color: #FFFFFF; font-weight: 700;
        letter-spacing: 0.2px;
    }
    .sih-banner p {
        margin: 0.15rem 0 0 0; font-size: 0.85rem; color: #9FB4C4;
    }
    .sih-pills {display: flex; gap: 0.5rem; flex-wrap: wrap;}
    .sih-pill {
        font-size: 0.72rem; font-weight: 600; padding: 0.3rem 0.7rem;
        border-radius: 999px; letter-spacing: 0.3px; white-space: nowrap;
    }
    .sih-pill-on {background: #1E4D33; color: #8FE3B0;}
    .sih-pill-off {background: #4D1E1E; color: #E38F8F;}
    .sih-pill-neutral {background: #2A4356; color: #BFD6E6;}

    .stTabs [data-baseweb="tab-list"] {gap: 4px;}
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0; padding: 0.5rem 1.1rem; font-weight: 600;
    }

    [data-testid="stChatMessage"] {
        border-radius: 12px; padding: 0.3rem 0.2rem;
    }
</style>
""", unsafe_allow_html=True)


def _render_banner() -> None:
    """A single glanceable strip: what this is, and whether the two demo
    differentiators are actually active right now - not just configured."""
    airgap_on = bool(config.ENFORCE_AIRGAP)
    approval_on = bool(config.REQUIRE_APPROVAL)
    st.markdown(f"""
    <div class="sih-banner">
        <div>
            <h1>🛢️ {config.APP_NAME}</h1>
            <p>{config.ORG} · {config.PROBLEM_ID} · {config.APP_SUBTITLE}</p>
        </div>
        <div class="sih-pills">
            <span class="sih-pill {'sih-pill-on' if airgap_on else 'sih-pill-off'}">
                {'🔒 AIR-GAP ENFORCED' if airgap_on else '⚠ AIR-GAP OFF'}</span>
            <span class="sih-pill {'sih-pill-on' if approval_on else 'sih-pill-off'}">
                {'✅ APPROVAL GATE ON' if approval_on else '⚠ APPROVAL GATE OFF'}</span>
            <span class="sih-pill sih-pill-neutral">{config.CHAT_MODEL}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


_render_banner()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init_state() -> None:
    if "agent" not in st.session_state:
        st.session_state.agent = agent_mod.Agent()
        try:
            audit.log_session_start()
        except Exception:  # noqa: BLE001 - never let logging break the UI
            pass
    if "history" not in st.session_state:
        st.session_state.history = []   # [{"role", "text", ...}] for display
    if "trace" not in st.session_state:
        st.session_state.trace = []     # tool events for the current answer


_init_state()


def _handle_events(events: list[dict]) -> None:
    """Fold agent.py events into what the Chat tab shows. Search/tool events
    go to the trace panel; only the final answer (or an error) becomes a
    chat bubble."""
    for ev in events:
        st.session_state.trace.append(ev)
        if ev["type"] == "answer":
            st.session_state.history.append({
                "role": "assistant", "text": ev["text"],
                "model": ev.get("model"), "elapsed_s": ev.get("elapsed_s"),
            })
        elif ev["type"] == "error":
            st.session_state.history.append(
                {"role": "assistant", "text": f"⚠️ {ev['text']}"})
        elif ev["type"] == "tool_declined":
            st.session_state.history.append({
                "role": "assistant",
                "text": f"_{ev['name']} was declined - continuing without it._",
            })


# ---------------------------------------------------------------------------
# Sidebar - system status, always visible
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### {config.APP_NAME}")
    st.caption(config.APP_SUBTITLE)

    health = llm.health()
    if health["reachable"]:
        st.success(f"Ollama reachable ({health.get('version', '?')})")
    else:
        st.error("Ollama not reachable")
        st.caption(health.get("error") or "Run `ollama serve` in a terminal.")

    kb_info = kb.info()
    if kb_info.get("ready"):
        st.info(f"Knowledge base: {kb_info.get('distinct_documents', 0)} "
                f"documents, {kb_info.get('chunks', 0)} chunks")
    else:
        st.warning("Knowledge base not built yet — see the Knowledge Base tab.")

    st.markdown("---")
    st.caption(f"Air-gap enforced: **{config.ENFORCE_AIRGAP}**")
    st.caption(f"Approval gate: **{config.REQUIRE_APPROVAL}**")
    st.caption(f"Chat model: `{config.CHAT_MODEL}`")

    if st.button("Reset conversation", use_container_width=True):
        st.session_state.agent.reset()
        st.session_state.history = []
        st.session_state.trace = []
        st.rerun()


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_chat, tab_kb, tab_trust, tab_airgap = st.tabs(
    ["💬 Chat", "📚 Knowledge Base", "🔒 Trust & Audit", "🌐 Air-Gap"])


# ---- Chat -------------------------------------------------------------
with tab_chat:
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["text"])
            if msg.get("model"):
                st.caption(f"{msg['model']} · {msg.get('elapsed_s', 0)}s "
                          f"· on-premise")

    pending = st.session_state.agent.pending
    if pending:
        st.warning(f"**Approval needed:** `{pending['name']}` wants to run.")
        with st.expander("What it wants to do", expanded=True):
            st.json(pending["arguments"])
        c1, c2 = st.columns(2)
        if c1.button("✅ Approve", type="primary", use_container_width=True):
            events = st.session_state.agent.approve()
            _handle_events(events)
            st.rerun()
        if c2.button("❌ Reject", use_container_width=True):
            events = st.session_state.agent.reject("Declined in UI")
            _handle_events(events)
            st.rerun()
    else:
        prompt = st.chat_input(
            "Ask about an SOP, work order, incident or equipment tag...")
        if prompt:
            st.session_state.history.append({"role": "user", "text": prompt})
            st.session_state.trace = []
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.spinner("Thinking..."):
                events = st.session_state.agent.ask(prompt)
            _handle_events(events)
            st.rerun()

    # The evidence trail for the answer that is currently on screen. This is
    # what turns "the AI found it" into "here is where it looked".
    if st.session_state.trace:
        with st.expander("🔍 What the assistant did to answer this",
                         expanded=False):
            for ev in st.session_state.trace:
                if ev["type"] == "tool_result":
                    st.markdown(f"**{ev['name']}**")
                    st.json(ev["arguments"])
                    res = ev["result"]
                    if isinstance(res, dict) and "results" in res:
                        for r in res["results"]:
                            st.markdown(f"- `[{r.get('citation')}]` "
                                       f"{(r.get('text') or '')[:220]}...")
                    else:
                        st.json(res)
                elif ev["type"] == "tool_error":
                    st.error(f"{ev['name']}: {ev['result'].get('error')}")

    generated = outputs.list_generated()
    if generated:
        st.markdown("---")
        st.markdown("**Generated files**")
        for f in generated[:8]:
            path = Path(f["path"])
            if path.exists():
                st.download_button(
                    f"⬇ {f['filename']} ({f['size_kb']} KB)",
                    data=path.read_bytes(), file_name=f["filename"],
                    key=f"dl_{f['filename']}")


# ---- Knowledge Base -----------------------------------------------------
with tab_kb:
    st.subheader("Corpus")
    uploaded = st.file_uploader(
        "Add documents (PDF, DOCX, images)", accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            dest = config.UPLOADS / f.name
            dest.write_bytes(f.getbuffer())
        st.success(f"Saved {len(uploaded)} file(s) to {config.UPLOADS}. "
                  f"Click Rebuild below to index them.")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔁 Rebuild index", type="primary"):
            bar = st.progress(0.0, text="Starting...")

            def _progress(msg: str, pct: float) -> None:
                bar.progress(min(max(pct, 0.0), 1.0), text=msg)

            report = kb.build_index(progress=_progress)
            bar.progress(1.0, text="Done")
            st.success(f"Indexed {report['chunks']} chunks from "
                      f"{report['documents']} documents in "
                      f"{report['elapsed_s']}s.")
            if report.get("embed_error"):
                st.warning(f"Embeddings failed: {report['embed_error']} "
                          f"(keyword search still works)")
            st.rerun()

    st.subheader("Indexed documents")
    docs = kb.documents()
    if docs:
        st.dataframe(
            [{"Doc ID": d["doc_id"], "Title": d["title"],
              "Type": d["doc_type"], "Chunks": d["chunks"],
              "Pages": d["pages"]} for d in docs],
            use_container_width=True, hide_index=True)
    else:
        st.info("No documents indexed yet.")

    with st.expander("Equipment tags known to the corpus"):
        tags = kb.all_tags()
        if tags:
            st.dataframe(
                [{"Tag": t["tag"], "Mentions": t["mentions"],
                  "Documents": ", ".join(t["documents"])} for t in tags],
                use_container_width=True, hide_index=True)
        else:
            st.caption("Build the index to see tags.")


# ---- Trust & Audit --------------------------------------------------------
with tab_trust:
    st.subheader("Audit chain")
    st.caption("Every tool call, approval, decline and generated file is "
              "written here, hash-chained to the record before it.")
    c1, c2 = st.columns(2)
    if c1.button("Verify chain integrity"):
        v = audit.verify()
        (st.success if v["ok"] else st.error)(v["message"])
    if c2.button("Export audit report"):
        st.text(audit.export_report())

    stats = audit.stats()
    st.metric("Total records", stats["total_records"])
    st.caption(f"This session ({stats['session_id']}): "
              f"{stats['this_session']} records")
    if stats["by_event"]:
        st.dataframe(
            [{"Event": k, "Count": v} for k, v in stats["by_event"].items()],
            use_container_width=True, hide_index=True)

    st.subheader("Sandbox controls")
    st.caption("What actually stops model-written code from doing damage.")
    controls = sandbox.describe_controls()
    st.json(controls)
    if st.button("Run sandbox self-test"):
        with st.spinner("Trying legitimate and malicious code, live..."):
            result = sandbox.self_test()
        (st.success if result["passed"] else st.error)(
            "All controls behaved as expected." if result["passed"]
            else "A control did not behave as expected — see below.")
        st.dataframe(result["cases"], use_container_width=True,
                    hide_index=True)


# ---- Air-Gap ---------------------------------------------------------------
with tab_airgap:
    st.subheader("Network isolation")
    st.caption("This process cannot open a socket to anything but "
              "loopback — proven, not just configured. Leave Wi-Fi on and "
              "run the test below; it deliberately tries to leave the "
              "machine and shows the attempt being blocked.")

    if st.button("🧪 Run air-gap self-test", type="primary"):
        with st.spinner("Attempting an outbound connection and DNS "
                       "lookup..."):
            result = netguard.self_test()
        (st.success if result["passed"] else st.error)(result["summary"])
        st.dataframe(result["probes"], use_container_width=True,
                    hide_index=True)

    st.markdown("---")
    st.text(netguard.attestation_text())
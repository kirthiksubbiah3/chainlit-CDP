# %%
import logging
import threading
import time
import io
import streamlit as st
from dotenv import load_dotenv
from agents.supervisor import Supervisor

load_dotenv()

# %%
st.title("🤖 Sentinel Mind")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display chat history
for entry in st.session_state.chat_history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])

# User input
user_input = st.chat_input("Type your message...")

if user_input:
    st.chat_message("user").markdown(user_input)
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # 📋 Setup log capture to display automation logs
    log_stream = io.StringIO()
    stream_handler = logging.StreamHandler(log_stream)
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    stream_handler.setFormatter(formatter)

    # Attach stream handler to relevant loggers
    for logger_name in [
        "agent",
        "browser_use",
        "controller",
        "dom",
        "message_manager",
        "browser",
    ]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(stream_handler)
        logger.propagate = False

    # Streamlit placeholders
    st.subheader("📋Logs")
    log_placeholder = st.empty()
    result_placeholder = st.empty()

    # 🧠 Run supervisor in thread to avoid blocking UI
    result_holder = {"value": None}

    def run_supervisor_workflow():
        supervisor_instance = Supervisor()
        workflow = supervisor_instance.workflow()
        app = workflow.compile()
        result_holder["value"] = app.invoke(
            {"messages": [{"role": "user", "content": user_input}]}
        )

    thread = threading.Thread(target=run_supervisor_workflow)
    thread.start()

    # 🔁 Live update log stream while agent runs
    while thread.is_alive():
        time.sleep(0.5)
        logs = log_stream.getvalue()
        log_placeholder.code(logs, language="log")

    # Final log update
    logs = log_stream.getvalue()
    log_placeholder.code(logs, language="log")

    # Display and store assistant response
    # pylint: disable=E1136, E1135
    result_value = result_holder["value"]  # pylint: disable=invalid-name
    if isinstance(result_value, dict) and "messages" in result_value:
        for m in result_value["messages"]:
            st.chat_message("assistant").markdown(m.content)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": m.content}
            )

# Prepare chat history text
chat_text = "" # pylint: disable=invalid-name
for entry in st.session_state.chat_history:
    chat_text += f"{entry['role']}: {entry['content']}\n"

# Download button (no confirmation)
st.download_button(
    "⬇️History", chat_text, file_name="chat_history.txt", mime="text/plain"
)

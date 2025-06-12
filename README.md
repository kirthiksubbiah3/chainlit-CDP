# 📦 Sentinel-Mind

A Streamlit-based chat UI powered by a LangGraph supervisor and a Playwright-backed browser-automation agent using AWS Bedrock (Anthropic Claude). Works on Windows, macOS, and Linux.

## Prerequisites

1. **Git** – verify with  
   git --version  
2. **Python** ≥ 3.12 – verify with  
   python3 --version  
3. **Node.js** & **npm** – verify with  
   node --version  
   npm --version  
4. **Playwright CLI** (optional) – for browser binaries:  
   npm install -g playwright

---

## Installation & Setup

1. **Clone the repository** and enter its directory  
   git clone https://github.com/YourOrg/Sentinel-Mind.git  
   cd Sentinel-Mind

2. **Create and activate a Python virtual environment**  
   • macOS / Linux  
     python3 -m venv .venv  
     source .venv/bin/activate  
   • Windows (PowerShell)  
     python -m venv .venv  
     .venv\Scripts\Activate.ps1  
   • Windows (CMD)  
     python -m venv .venv  
     .venv\Scripts\activate.bat

3. **Upgrade pip & install dependencies**  
   pip install --upgrade pip  
   pip install -r requirements.txt

4. **Install Playwright browser binaries**  
   If you see errors about missing browsers:  
   npx playwright install

5. **Configure environment variables**  
   Copy the sample file and fill in your credentials:  
   cp .env.example .env  
   Open `.env` and set:

```
AWS_ACCESS_KEY_ID="YOUR_AWS_KEY"
AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET"
AWS_REGION="us-east-1"
anthem_username="YOUR_USERNAME"
anthem_password="YOUR_PASSWORD"
```

---

## Project Structure

Sentinel-Mind/  
├── agents/                            Tool wrappers for LangGraph agents  
│   ├── browser_automation_agent.py    Defines `run_browser_agent()` & React agent  
│   └── supervisor.py                  Builds the LangGraph supervisor workflow  
├── logs/                              Chat transcripts
├── models/                            LLM client wrappers  
│   └── bedrock.py                     ChatBedrock wrapper for AWS Anthropic Claude   
├── .env.example                       Template for `.env`  
├── .gitignore                         Ignores venv, .env, caches, logs, etc.  
├── main.py                            Streamlit front end & live log streaming  
├── README.md                          This file  
└── requirements.txt                   Pinned Python dependencies  

---

## Components & Flow

1. **models/bedrock.py**  
Wraps LangChain’s `ChatBedrock` to communicate with Anthropic Claude via AWS Bedrock.

2. **agents/browser_automation_agent.py**  
- Loads `.env` credentials  
- Instantiates the Claude model:  
  `model = bedrock(...).get_model_details()`  
- Defines `run_browser_agent(task: str) → str` that uses Playwright (via `browser-use`) to navigate, fill forms, and scrape  
- Registers a React-style agent with `create_react_agent(...)`

3. **agents/supervisor.py**  
- Imports `browser_agent`  
- Builds a LangGraph Supervisor that routes “URL/health check” tasks to the browser agent

4. **main.py**  
- Renders a Streamlit chat interface  
- Captures user messages in `st.session_state.chat_history`  
- Runs the supervisor workflow in a background thread to avoid blocking  
- Streams low-level logs live under the chat window  
- Displays the agent’s responses when complete  
- Provides a “⬇️History” button to download the full transcript  

---

## Running the App

1. Ensure your virtual environment is active and `.env` is configured.  
2. From the project root, run:  
```streamlit run main.py```
3. A browser window will open with the chat UI:  
- Type your task (e.g., “Check Anthem demo portal login health”).  
- Watch live automation logs under **Logs**.  
- See the agent’s response in the chat pane.  
- Click **⬇️History** to download the conversation transcript.

---

## Platform-Specific Tips

- **Windows & asyncio**  
If you encounter a `NotImplementedError` from Playwright/asyncio, uncomment this in `browser_automation_agent.py`:
```python
import asyncio, sys
if sys.platform == "win32":
   asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

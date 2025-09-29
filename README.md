# SFLabs AI Assistant

This is an AI assistant with agents and LLM built with

- [Chainlit](https://docs.chainlit.io/)
- [Langchain](https://www.langchain.com/)
- [Langgraph](https://www.langchain.com/langgraph)
- [MCP](https://www.langchain.com/langgraph)

---

## 🧩 Requirements

- Python version, check this [file](./.python-version)
- AWS credentials with access to Bedrock and Claude models
- `.env` file with credentials, see [example](!.env.example)

---

## 📦 Setup

1. Clone the repo
2. Create and activate a virtual environment:
3. Install the modules
4. Run the app with chainlit

```bash
# optionally set and activate venv if required
uv venv
source .venv/bin/activate  # On Windows: venv\Scripts\activate

uv sync
uv run chainlit run src/app.py -w
```

## Instructions to run Grafana mcp server

- We use Streamable HTTP Mode
- You must expose port 8000 using the -p flag.
- Use the following commands to run the server

```bash
docker pull mcp/grafana
docker run --rm -p 8000:8000 \
    -e GRAFANA_URL=<Your GRAFANA_URL> \
    -e GRAFANA_API_KEY=<Your GRAFANA_API_KEY> \
    mcp/grafana -t streamable-http
```

## Instructions to run Atlassian mcp server

- We use Streamable HTTP Mode
- You must expose port 9000 using the -p flag.
- Use the following commands to run the server

```bash
docker pull ghcr.io/sooperset/mcp-atlassian:latest
docker run --rm -p 9000:9000 \
    -e CONFLUENCE_URL="https://your-company.atlassian.net/wiki" \
    -e CONFLUENCE_USERNAME="your.email@company.com" \
    -e CONFLUENCE_API_TOKEN="your_atlassian_api_token" \
    ghcr.io/sooperset/mcp-atlassian:latest -t streamable-http --port 9000
```

## Observability graph details

```mermaid
flowchart TD
    Start([START])
    Agent[Agent Node]
    Tools[Tools Node]
    Evaluator[Evaluator Node]
    Router[Router Node]
    End([END])

    Start --> Agent

    Agent -- "safe_tools_condition: tools" --> Tools
    Agent -- "safe_tools_condition: evaluator" --> Evaluator
    Agent -- "safe_tools_condition: END" --> End

    Tools --> Agent

    Evaluator --> Router
    Router --> Agent
```

## Slack Integration

- Follow the steps in the [Chainlit Slack document](https://docs.chainlit.io/deploy/slack)
- Fill the request URL under
  [Event Subscriptions](https://api.slack.com/apps/A09AEQJLFHA/event-subscriptions).
- You can use ngrok for generating https url of your chainlit app for development
  purpose, by running ngrok on whichever port you are running chainlit,
  for ex. ngrok http 8000. You can use the generated ngrok url in the next step.
- The request URL will be `https://<chainlit url>/slack/events`. Chainlit has inbuilt
  handler for it.
- Verify the request URL by pressing verify button.
- Start chatting.

## Running with Docker

You can run the Sentinel Mind application directly using Docker:

```bash
docker run \
  --env-file .env \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/secrets.yaml:/app/secrets.yaml \
  <docker-image-name>:<tag>
```

### Notes

- Replace `<docker-image-name>:<tag>` with your actual Docker image name and tag
- Make sure your `.env` file contains all required environment variables
- Ensure `config.yaml` exists in your current directory
- Create a `secrets.yaml` file (you can copy from `secrets.example.yaml`
  and modify as needed)
- You can add `-p 8000:8000` to expose the web interface (replace the first
  port with your desired local port)

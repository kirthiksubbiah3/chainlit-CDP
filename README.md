# AI Observe Assistant

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

chainlit create-secret #To create secret
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
    -e JIRA_URL="https://your-company.atlassian.net/" \
    -e JIRA_USERNAME="your.email@company.com"\
    -e JIRA_API_TOKEN="your_atlassian_api_token"\
    ghcr.io/sooperset/mcp-atlassian:latest --transport streamable-http --port 9000
```

Commit Message & Branch Naming Rules

✅ Commit Message Format

All commit messages must match one of the following patterns:
Allowed types
build | ci | docs | feat | fix | perf | refactor | style | test | chore | revert | merge
Format
<type>(optional-scope): short description
Valid examples
feat(auth): add login validationfix: resolve crash on startupdocs(readme): update setup stepschore: update dependenciesmerge: branch develop into mainNotes added by release scriptProject initial commit
❌ Invalid examples
added new featurebug fixFEAT: something
🌿 Branch Naming Convention
Branch names must follow one of these patterns:
Standard branches
feature/<name>-<number>hotfix/<name>-<number>uat/<name>-<number>pilot/<name>-<number>
OR using hyphens
feature-<name>-<number>hotfix-<name>-<number>uat-<name>-<number>pilot-<name>-<number>
Special allowed branches
livetraintmo/main
Valid examples
feature-login-123hotfix/payment-45uat-search-9pilot/onboarding-101live
❌ Invalid examples
feature_loginbugfix-123maindev-feature-1

# chainlit-CDP

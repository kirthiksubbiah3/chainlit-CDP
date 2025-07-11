# Claude 3 Chainlit Chatbot (via AWS Bedrock)

This is a simple chatbot app built using [Chainlit](https://docs.chainlit.io/) and Anthropic's Claude 3 model served through AWS Bedrock.

---

## 🧩 Requirements

- Python 3.9 or higher
- AWS credentials with access to Bedrock and Claude models
- `.env` file with credentials, see [example](!.env.example)

---

## 📦 Setup

1. Clone the repo
2. Create and activate a virtual environment:
3. Install the modules
4. Run the app with chainlit

```bash
python -m venv venv

source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r dev_requirements.txt # when developing locally, use requirements.txt for deployments

chainlit run app.py -w
```

## Instructions to run Browser automation with playwright using modified playwright mcp server
1. Go to the playwright-mcp directory
2. Execute npm install
3. Execute npm run build, if there are any issues run the below three commands. Else the commands can be skipped
4. npm install zod-to-json-schema
5. npm link @modelcontextprotocol/sdk
6. npm install --save-dev @types/mime
7. Execute npm run build after resolving the errors 

## Instructions to run Grafana mcp server
- We use Streamable HTTP Mode
- You must expose port 8000 using the -p flag.
- Use the following commands to run the server

```bash
docker pull mcp/grafana
docker run --rm -p 8000:8000 -e GRAFANA_URL=<Your GRAFANA_URL> -e GRAFANA_API_KEY=<Your GRAFANA_API_KEY> mcp/grafana -t streamable-http
```

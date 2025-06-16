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

pip install -r requirements.txt

chainlit run main.py -w
```

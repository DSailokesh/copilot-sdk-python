# Web search agent — Claude Agent SDK on Azure App Service

A small FastAPI app. You ask a question ("What is the score in today's India vs New Zealand match?"),
a Claude Agent SDK agent searches the web, and the app returns a short answer with sources.

```
app/
  main.py         API: /health, POST /api/ask, GET /api/ask/stream (SSE), / (test page)
  agent.py        The agent: WebSearch + WebFetch only, every other built-in tool blocked
  config.py       Settings from environment variables
  static/index.html  Test page with live progress
requirements.txt  startup.sh  .env.example
```

## How it works

1. The question goes to the agent with a system prompt that includes today's date (so "today" is correct).
2. The agent may only use `WebSearch` and `WebFetch`. Shell, file and sub-agent tools are blocked, and no settings or CLAUDE.md are loaded from disk.
3. The streaming endpoint sends each search and fetch as a progress event, then the answer.
4. Limits: max turns, a timeout per question, and a cap on questions running at the same time.

## Which provider supports web search

Web search is a server-side tool run by the model provider, so it depends on where Claude runs:

| Provider | Web search |
|---|---|
| Anthropic API | Supported |
| Microsoft Foundry | Supported per Anthropic's docs; confirm on your deployment |
| Amazon Bedrock | Not supported (WebFetch with specific URLs still works) |
| Your AI gateway | Works only if it passes the web search tool through to a provider that supports it |

## Run locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in ONE provider block
set -a; . ./.env; set +a      # load the variables into this shell
uvicorn app.main:app --reload
```

Open http://localhost:8000 and ask a question, or:

```bash
curl -s -X POST localhost:8000/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"What is the score in today'\''s India vs New Zealand match?"}'

curl -N "localhost:8000/api/ask/stream?question=Latest%20India%20vs%20New%20Zealand%20score"
```

## Deploy to Azure App Service (Linux, Python)

Needs the Azure CLI and a resource group.

```bash
RG=rg-agent-demo
APP=agent-websearch-$RANDOM
LOCATION=centralindia

# 1. Create the plan and app and deploy this folder (builds with pip on the server)
az webapp up --resource-group $RG --name $APP --location $LOCATION \
  --runtime "PYTHON:3.12" --sku B2

# 2. Startup command
az webapp config set -g $RG -n $APP --startup-file "sh startup.sh"

# 3. Settings (one provider block from .env.example)
az webapp config appsettings set -g $RG -n $APP --settings \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  ANTHROPIC_API_KEY="<key>" \
  AGENT_MODEL="" APP_TIME_ZONE="Asia/Kolkata" AGENT_TIMEOUT_SECONDS=120

# 4. Health check and logs
az webapp config set -g $RG -n $APP --generic-configurations '{"healthCheckPath":"/health"}'
az webapp log config -g $RG -n $APP --docker-container-logging filesystem
az webapp log tail -g $RG -n $APP
```

Then open `https://$APP.azurewebsites.net`.

For redeploys after code changes: `az webapp up -g $RG -n $APP` again from this folder.

### Production notes

- **Secrets**: put the API key in Key Vault and reference it from app settings (`@Microsoft.KeyVault(...)`), or use Foundry with the app's managed identity.
- **Timeouts**: App Service ends HTTP requests after about 230 seconds. Keep `AGENT_TIMEOUT_SECONDS` well below that, and prefer the streaming endpoint so the browser sees progress.
- **Memory**: each question starts a Claude Code process. Use B2/P1v3 or larger and keep `AGENT_MAX_CONCURRENT` small; scale out for more users.
- **Writable folder**: runs use `/tmp/agent-runs` and delete their folder afterwards.
- **Pin versions** in `requirements.txt` after the first working deploy, and pin `AGENT_MODEL`.
- **Option names** (`allowed_tools`, `disallowed_tools`, `setting_sources`) can change between SDK versions; check them against the version you pin.

# Power BI MCP Assistant

A natural language interface for Power BI, powered by Claude and the [Model Context Protocol](https://modelcontextprotocol.io/). Ask questions about your Power BI data in plain English — Claude handles the rest.

Available as both a browser-based chat UI (Streamlit) and a terminal REPL.

---

## How it works

This app connects Claude to Microsoft's Power BI MCP server. When you ask a question, Claude discovers the available Power BI tools, decides which ones to call, executes them, and returns an answer — often with an auto-rendered chart. The entire loop is agentic: Claude can chain multiple tool calls together to answer complex questions without you writing any DAX.

## Features

- **Natural language queries** — no DAX required
- **Agentic loop** — Claude iteratively calls tools until it has a complete answer
- **Auto-rendered charts** — bar, line, pie, and metric cards generated from query results
- **Two interfaces** — Streamlit web UI and terminal CLI (REPL)
- **Microsoft authentication** — MSAL device code flow with local token caching
- **Conversation memory** — full multi-turn context within a session

## Prerequisites

- Python 3.10+
- A [Claude API key](https://console.anthropic.com/)
- A Microsoft account with access to a Power BI workspace
- Access to Microsoft's Power BI MCP server (`https://api.fabric.microsoft.com/v1/mcp/powerbi`)

## Installation

```bash
git clone https://github.com/your-username/Connecting_PowerBI_MCP.git
cd Connecting_PowerBI_MCP

python -m venv .venv
source .venv/bin/activate      # Linux/Mac
# or
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

## Configuration

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```env
CLAUDE_API_KEY=sk-ant-...

# Optional — leave blank to use device code flow (recommended)
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
```

That's all you need for most setups. The app defaults to device code authentication, which means no Azure app registration is required — you just sign in through your browser on first run.

If you need a custom Azure app registration (e.g. for a service account or specific tenant), see [docs/azure-setup.md](docs/azure-setup.md).

## Usage

### Streamlit UI

```bash
streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser. On first run, you'll be prompted to authenticate with Microsoft via device code flow.

### CLI

```bash
python main.py
```

Available commands in the REPL:

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/tools` | List available Power BI tools |
| `/clear` | Clear conversation history |
| `/history` | Show conversation length |
| `/exit` | Quit |

## Project structure

```
├── streamlit_app.py         # Streamlit entry point
├── main.py                  # CLI entry point
├── core/
│   └── orchestrator.py      # Agentic loop
├── clients/
│   ├── claude_client.py     # Anthropic API wrapper
│   ├── simple_mcp_client.py # Power BI MCP client
│   ├── http_transport.py    # JSON-RPC over HTTP POST
│   └── tool_converter.py    # MCP ↔ Claude format conversion
├── auth/
│   ├── manager.py           # MSAL device code flow
│   └── token_cache.py       # Encrypted local token cache
├── config/
│   └── settings.py          # Pydantic-based configuration
├── streamlit_ui/
│   ├── session_manager.py   # Streamlit session lifecycle
│   ├── async_runner.py      # Thread-safe async bridge
│   ├── components.py        # UI components
│   └── charts/              # Chart detection and rendering
├── cli/                     # CLI interface
├── docs/                    # Setup and troubleshooting guides
├── .env.example             # Environment variable template
└── requirements.txt
```

## Authentication

On first run, the app displays a device code and URL:

```
To sign in, visit https://microsoft.com/devicelogin and enter the code: XXXXX-XXXXX
```

After signing in through your browser, the token is cached locally at `~/.powerbi-mcp/token_cache.bin` and auto-refreshes on subsequent runs.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues.

## License

MIT — see [LICENSE](LICENSE).

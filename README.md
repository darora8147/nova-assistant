# 🤖 Nova – Personal AI Assistant

A fully local + cloud-hybrid AI chatbot that works **online and offline**.

---

## 📁 Project Structure

```
my-assistant/
│
├── backend/
│   ├── __init__.py       ← makes backend a Python package
│   ├── router.py         ← detects online/offline, picks the right LLM
│   ├── memory.py         ← short-term (session) + long-term (ChromaDB) memory
│   ├── tools.py          ← calculator, file read/write, web search, datetime
│   └── assistant.py      ← core brain: builds prompts, calls LLM, runs tools
│
├── frontend/
│   ├── index.html        ← the full chat UI (HTML + CSS + JS, no framework)
│   └── static/           ← put images/icons here if needed
│
├── memory_db/            ← ChromaDB stores conversations here (auto-created)
│
├── server.py             ← FastAPI server (all API routes)
├── requirements.txt      ← all Python dependencies
├── .env                  ← your config (API keys, model names, etc.)
├── setup.sh              ← one-time setup script (Linux/macOS)
├── start.sh              ← start the server (Linux/macOS)
└── start.bat             ← start the server (Windows)
```

---

## 🚀 How to Run (Step by Step)

### Step 1 – Install Python
Download Python 3.10 or higher from https://www.python.org/downloads/

### Step 2 – Open a terminal in this folder
```bash
cd my-assistant
```

### Step 3 – Run the setup script (first time only)
**Linux / macOS:**
```bash
bash setup.sh
```

**Windows (manual steps):**
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Then install Ollama from https://ollama.com and run:
```bat
ollama pull mistral
```

### Step 4 – Start the server
**Linux / macOS:**
```bash
bash start.sh
```

**Windows:**
```bat
start.bat
```

### Step 5 – Open your browser
Go to: **http://localhost:8000**

---

## ⚙️ Configuration (.env file)

Open the `.env` file and change these settings:

| Setting | Default | Description |
|---|---|---|
| `OFFLINE_MODEL` | `mistral` | Local model to use when offline |
| `ONLINE_MODEL` | `gpt-4o-mini` | Cloud model to use when online |
| `OPENAI_API_KEY` | (empty) | Add your OpenAI key to enable online mode |
| `USER_NAME` | `Friend` | Your name (the assistant will use it) |
| `ASSISTANT_NAME` | `Nova` | What to call your assistant |
| `MEMORY_WINDOW` | `20` | How many past messages to remember per session |

---

## 🤖 Available AI Models (Offline / Ollama)

| Model | RAM needed | Speed | Quality |
|---|---|---|---|
| `phi3` | 4 GB | Very fast | Good for simple tasks |
| `mistral` | 8 GB | Fast | Great all-rounder ✅ recommended |
| `llama3.2` | 8 GB | Fast | Excellent reasoning |
| `llama3.1:8b` | 16 GB | Medium | Very high quality |

To download a different model:
```bash
ollama pull llama3.2
```
Then update `OFFLINE_MODEL=llama3.2` in your `.env` file.

---

## 🛠️ Tools the Assistant Can Use

| Tool | What it does |
|---|---|
| `calculator` | Solves math: `sqrt(144)`, `2**32`, `15% of 2500` |
| `read_file` | Reads any local file |
| `write_file` | Creates/writes local files |
| `list_files` | Lists files in a folder |
| `get_datetime` | Returns today's date and time |
| `web_search` | Searches DuckDuckGo (online mode only) |

---

## 🔧 Troubleshooting

**Server won't start:**
- Make sure you ran `pip install -r requirements.txt`
- Check if port 8000 is in use: `lsof -i :8000` (Mac/Linux)

**Ollama errors:**
- Make sure Ollama is running: `ollama serve`
- Make sure you pulled a model: `ollama pull mistral`

**Online mode not working:**
- Add your `OPENAI_API_KEY` to the `.env` file

**Slow responses:**
- Switch to a smaller model like `phi3` in `.env`
- Close other heavy apps to free up RAM

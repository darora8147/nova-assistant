#!/usr/bin/env bash
# ─────────────────────────────────────────────────────
#  start.sh  –  Start your Personal AI Assistant
# ─────────────────────────────────────────────────────

set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Nova – Personal AI Assistant       ║"
echo "╚══════════════════════════════════════╝"
echo ""

# 1. Activate virtual environment if it exists
if [ -d "venv" ]; then
  echo "✅ Activating virtual environment..."
  source venv/bin/activate
else
  echo "⚠️  No venv found. Using system Python."
fi

# 2. Check if Ollama is running (for offline mode)
echo "🔍 Checking Ollama..."
if command -v ollama &> /dev/null; then
  if ! pgrep -x "ollama" > /dev/null; then
    echo "   Starting Ollama in background..."
    ollama serve &>/dev/null &
    sleep 2
  fi
  echo "✅ Ollama is ready."
else
  echo "⚠️  Ollama not found. Online mode only."
fi

# 3. Start the FastAPI server
echo ""
echo "🚀 Starting server at http://127.0.0.1:8000"
echo "   Press Ctrl+C to stop."
echo ""

python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

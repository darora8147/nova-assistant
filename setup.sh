#!/usr/bin/env bash
# ─────────────────────────────────────────────────────
#  setup.sh  –  One-time setup for Personal Assistant
# ─────────────────────────────────────────────────────

set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Nova Setup – First Time Install    ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Step 1: Python check ─────────────────────────────
echo "Step 1/5 – Checking Python..."
if ! command -v python3 &> /dev/null; then
  echo "❌ Python 3 not found. Install from https://www.python.org"
  exit 1
fi
PYVER=$(python3 --version)
echo "✅ Found $PYVER"

# ── Step 2: Create virtual environment ───────────────
echo ""
echo "Step 2/5 – Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment created."

# ── Step 3: Install Python packages ──────────────────
echo ""
echo "Step 3/5 – Installing Python packages..."
pip install --upgrade pip -q
pip install -r requirements.txt
echo "✅ Packages installed."

# ── Step 4: Install Ollama ────────────────────────────
echo ""
echo "Step 4/5 – Installing Ollama (local LLM runner)..."
if command -v ollama &> /dev/null; then
  echo "✅ Ollama already installed."
else
  echo "   Downloading Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
  echo "✅ Ollama installed."
fi

# ── Step 5: Pull a model ──────────────────────────────
echo ""
echo "Step 5/5 – Downloading AI model (mistral ~4 GB, first time only)..."
echo "   This may take a few minutes depending on your internet speed."
ollama pull mistral
echo "✅ Model ready."

# ── Done ──────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║   ✅ Setup complete!                 ║"
echo "║                                      ║"
echo "║   Run:  bash start.sh               ║"
echo "║   Then open: http://localhost:8000   ║"
echo "╚══════════════════════════════════════╝"
echo ""

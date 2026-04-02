#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  switch_model.sh
#  Run this to pick the best AI model for your machine's RAM.
#  Usage:  bash switch_model.sh
# ─────────────────────────────────────────────────────────────

# Detect available RAM in GB
if [[ "$OSTYPE" == "darwin"* ]]; then
    TOTAL_RAM_KB=$(sysctl -n hw.memsize | awk '{print $1/1024}')
    FREE_RAM_KB=$(vm_stat | awk '/Pages free/ {print $3*4096/1024}' | tr -d '.')
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    FREE_RAM_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
else
    TOTAL_RAM_KB=8000000
    FREE_RAM_KB=2000000
fi

TOTAL_GB=$(echo "scale=1; $TOTAL_RAM_KB/1024/1024" | bc 2>/dev/null || echo "?")
FREE_GB=$(echo "scale=1; $FREE_RAM_KB/1024/1024" | bc 2>/dev/null || echo "?")

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║   Model Switcher – Nova Personal Assistant ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo "  Your RAM: ${TOTAL_GB} GB total, ~${FREE_GB} GB free right now"
echo ""
echo "  Pick your model:"
echo ""
echo "  1) phi3:mini    → 1.8 GB RAM  │ Very fast │ Good for chat, simple tasks"
echo "  2) gemma2:2b    → 2.0 GB RAM  │ Fast      │ Better reasoning than phi3"
echo "  3) mistral      → 4.1 GB RAM  │ Medium    │ Great all-rounder"
echo "  4) llama3.2:3b  → 2.0 GB RAM  │ Fast      │ Excellent quality"
echo "  5) llama3.1:8b  → 5.5 GB RAM  │ Slow      │ Best quality (needs 8GB+)"
echo ""
read -p "  Enter number (1-5): " choice

case $choice in
  1) MODEL="phi3:mini"    CTX=1024 THREADS=4 ;;
  2) MODEL="gemma2:2b"    CTX=1024 THREADS=4 ;;
  3) MODEL="mistral"      CTX=2048 THREADS=4 ;;
  4) MODEL="llama3.2:3b"  CTX=2048 THREADS=4 ;;
  5) MODEL="llama3.1:8b"  CTX=2048 THREADS=2 ;;
  *) echo "Invalid choice"; exit 1 ;;
esac

echo ""
echo "  Pulling $MODEL from Ollama (may take a few minutes first time)..."
ollama pull "$MODEL"

# Update .env
sed -i.bak "s/^OFFLINE_MODEL=.*/OFFLINE_MODEL=$MODEL/" .env
sed -i.bak "s/^OLLAMA_NUM_CTX=.*/OLLAMA_NUM_CTX=$CTX/" .env
sed -i.bak "s/^OLLAMA_NUM_THREAD=.*/OLLAMA_NUM_THREAD=$THREADS/" .env
rm -f .env.bak

echo ""
echo "  ✅ Switched to $MODEL"
echo "  ✅ Context window: $CTX tokens"
echo "  ✅ CPU threads: $THREADS"
echo ""
echo "  Restart the server to apply:  bash start.sh"
echo ""

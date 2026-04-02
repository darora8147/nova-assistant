# 🚀 Deploying Nova on a Server (Free Options)

## Option 1 — Railway.app (Easiest, Free tier)

### Step 1 — Create a free account
Go to https://railway.app and sign up with GitHub.

### Step 2 — Prepare your project for Railway

Create this file in your project root:

**Procfile** (no extension):
```
web: uvicorn server:app --host 0.0.0.0 --port $PORT
```

**runtime.txt**:
```
python-3.11.0
```

### Step 3 — Problem: Ollama won't run on Railway
Railway doesn't allow Ollama (no GPU, no large binaries).
**Solution**: Use OpenAI API as the model when deployed.

In your `.env` on Railway, set:
```
OPENAI_API_KEY=sk-your-key-here
OFFLINE_MODEL=phi3:mini
ONLINE_MODEL=gpt-4o-mini
```

### Step 4 — Push to GitHub
```bash
git init
git add .
git commit -m "Nova personal assistant"
git remote add origin https://github.com/yourusername/nova-assistant.git
git push -u origin main
```

### Step 5 — Deploy on Railway
1. Go to railway.app → New Project → Deploy from GitHub
2. Select your repo
3. Add environment variables (copy from your .env)
4. It auto-deploys — you get a URL like `nova-assistant.up.railway.app`

---

## Option 2 — Oracle Cloud Free Tier (Always Free, Best Option)

Oracle gives you a **free VM forever** — no credit card expiry, no trial.
This lets you run Ollama + the full app on a real Linux server.

### Step 1 — Create Oracle Cloud account
Go to https://cloud.oracle.com → Sign up for Always Free

### Step 2 — Create a VM
1. Go to Compute → Instances → Create Instance
2. Choose: **Ubuntu 22.04**, Shape: **VM.Standard.A1.Flex** (4 OCPU, 24GB RAM FREE)
3. Download the SSH key pair
4. Click Create

### Step 3 — Connect to your VM
```bash
ssh -i ~/Downloads/your-key.key ubuntu@YOUR_VM_IP
```

### Step 4 — Install everything on the server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3:mini

# Clone/upload your project
# Option A: clone from GitHub
git clone https://github.com/yourusername/nova-assistant.git
cd nova-assistant

# Option B: upload via SCP from your Windows machine
# scp -i your-key.key -r C:\path\to\my-assistant ubuntu@YOUR_IP:/home/ubuntu/

# Setup Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy your .env file and fill in your details
nano .env
```

### Step 5 — Run with PM2 (keeps it alive forever)
```bash
# Install Node + PM2 process manager
sudo apt install nodejs npm -y
sudo npm install -g pm2

# Start Ollama as a service
pm2 start "ollama serve" --name ollama
pm2 save

# Start Nova
pm2 start "uvicorn server:app --host 0.0.0.0 --port 8000" --name nova
pm2 save
pm2 startup   # follow the command it prints
```

### Step 6 — Open port 8000 in Oracle firewall
1. Go to Oracle Cloud → Networking → Virtual Cloud Networks
2. Click your VCN → Security Lists → Default Security List
3. Add Ingress Rule: Source=0.0.0.0/0, Port=8000

Also open it in Ubuntu:
```bash
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save
```

### Step 7 — Access your chatbot from anywhere
Open browser: `http://YOUR_VM_IP:8000`

### Step 8 — (Optional) Add a free domain + HTTPS
```bash
# Install Nginx
sudo apt install nginx -y

# Install Certbot for free SSL
sudo apt install certbot python3-certbot-nginx -y

# Point a free domain (from freenom.com or cloudflare)
# Then run:
sudo certbot --nginx -d yourdomain.com
```

Now access at: `https://yourdomain.com` 🎉

---

## Option 3 — Run on your Windows PC, access from anywhere (Ngrok)

If you just want to access it from your phone/another device temporarily:

```bat
# Install ngrok from https://ngrok.com (free)
# Then while your server is running:
ngrok http 8000
```

It gives you a URL like `https://abc123.ngrok.io` — accessible from anywhere.

---

## Quick Comparison

| Option         | Cost    | Ollama | Always On | Difficulty |
|----------------|---------|--------|-----------|------------|
| Railway.app    | Free*   | ❌     | ✅        | Easy       |
| Oracle Cloud   | Free    | ✅     | ✅        | Medium     |
| Ngrok (local)  | Free    | ✅     | ❌        | Easy       |

*Railway free tier has usage limits

**Recommendation**: Use **Oracle Cloud** for full features including Ollama offline mode.
Use **Railway** if you're okay with OpenAI API and want the easiest setup.

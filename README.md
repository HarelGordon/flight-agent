# ✈️ Flight Price Alert Agent

An automated flight price monitoring agent that scans Google Flights daily and sends a Telegram alert when prices drop below a target threshold.

## 🚀 Features

- Monitors **TLV → Sofia (SOF)** and **TLV → Bucharest (OTP)** routes
- Checks **5, 6, and 7-night** trip combinations
- Scans departure dates from **July 12 to August 9**
- Sends instant **Telegram notifications** when deals are found
- Runs **fully automated** in the cloud — even when your PC is off

## 🏗️ Architecture
```
GitHub Actions (daily scheduler)
        ↓
Docker Container (Python 3.11)
        ↓
fast-flights (unlimited, free) — 5 & 7 nights
SerpAPI Google Flights — 6 nights + monthly overview
        ↓
Telegram Bot API → Personal alert 📲
```

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.11 | Core scripting |
| Docker | Containerization |
| GitHub Actions | Cloud scheduler (CI/CD) |
| SerpAPI | Google Flights data |
| fast-flights | Free flight scraping |
| Telegram Bot API | Price alerts |
| GitHub Secrets | Secure API key management |

## ⚙️ How It Works

1. GitHub Actions triggers the workflow every day at 09:00 (Israel time)
2. A Docker container is built and launched on GitHub's cloud servers
3. The agent queries flight prices across all date combinations
4. If a price is found below the threshold — a Telegram message is sent instantly
5. If no deals found — a summary message is sent

## 🔧 Setup

### 1. Clone the repository
```bash
git clone https://github.com/HarelGordon/flight-agent.git
cd flight-agent
```

### 2. Set environment variables
Create a `.env` file:
```
TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
SERPAPI_KEY=your_key
```

### 3. Run locally with Docker
```bash
docker build -t flight-agent .
docker run --env-file .env flight-agent
```

### 4. Deploy to GitHub Actions
Add your secrets to **Settings → Secrets and variables → Actions** and push to `main`.

## 📁 Project Structure
```
flight-agent/
├── main.py                  # Core agent logic
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
├── .github/
│   └── workflows/
│       └── flight_check.yml # GitHub Actions scheduler
└── .env                     # Local secrets (not committed)
```

## 🔒 Security

All API keys are stored as **GitHub Secrets** — never hardcoded or committed to the repository.
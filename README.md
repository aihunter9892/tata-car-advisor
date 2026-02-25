# 🚗 Tata Car Buying Advisor — Agentic AI

**Stack:** Python Flask · Gemini 2.5 Flash · Groq Llama-3.3-70b (auto-fallback)  
**Deploy:** GitHub → GitHub Actions CI/CD → AWS App Runner

---

## 📁 Project Structure

```
tata_advisor/
├── database.py                   ← car specs + city profiles (data only)
├── tools.py                      ← 4 agent tools: weather, cars, fuel, TCO
├── agents.py                     ← GeminiAgent, GroqAgent, run_agent()
├── app.py                        ← Flask routes + competitor guardrail
├── apprunner.yaml                ← AWS App Runner build/run config
├── requirements.txt
├── .env.example
├── static/
│   └── index.html
└── .github/
    └── workflows/
        └── deploy.yml            ← CI/CD pipeline
```

---

## 🖥️ Local Development

```bash
git clone https://github.com/YOUR_USERNAME/tata-car-advisor.git
cd tata-car-advisor
pip install -r requirements.txt
cp .env.example .env
python app.py   # → http://localhost:5000
```

---

## 🚀 Deployment — 4 Steps

### STEP 1 — Push to GitHub
```bash
git init && git add . && git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/tata-car-advisor.git
git branch -M main && git push -u origin main
```

### STEP 2 — Create AWS App Runner Service
1. AWS Console → **App Runner** → **Create service**
2. Source: **Source code repository** → connect GitHub → select repo + branch `main`
3. Deployment trigger: **Automatic** (enables CI/CD)
4. Runtime: Python 3 · Port: `8080`
5. Build: `pip install -r requirements.txt`
6. Start: `gunicorn app:app --bind 0.0.0.0:8080 --workers 2 --timeout 120`
7. **Environment variables** → add `GEMINI_API_KEY` and `GROQ_API_KEY`
8. Region: `ap-south-1` (Mumbai) · CPU: 1 vCPU · Memory: 2 GB
9. Deploy → copy the **Service ARN** from the service page

### STEP 3 — Add GitHub Secrets
IAM → create user `github-actions-tata` → attach `AWSAppRunnerFullAccess` → create access key

GitHub repo → Settings → Secrets → Actions:

| Secret | Value |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |
| `APP_RUNNER_CONNECTION_ARN` | App Runner → Source connection ARN |

### STEP 4 — Every Deploy is Just a Push
```bash
git add . && git commit -m "your change" && git push origin main
```
Pipeline: Install → 3 CI tests → Deploy to App Runner → prints live URL

---

## 💰 Cost (App Runner vs Elastic Beanstalk)

| | App Runner | Elastic Beanstalk |
|--|--|--|
| Workshop use | ~$3–8/mo | ~$17–23/mo |
| Setup steps | 4 | 10+ |
| Scaling | Automatic | Manual |
| Config files | 1 (`apprunner.yaml`) | 3+ |

---

*UpGrad KnowledgeHut · AI Engineering Workshop · Agentic AI Module*

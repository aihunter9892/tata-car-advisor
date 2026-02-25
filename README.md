# 🚗 Tata Car Buying Advisor — Agentic AI

**Stack:** Python Flask · Gemini 2.5 Flash · Groq Llama-3.3-70b (fallback)  
**Deploy:** GitHub Actions → AWS Elastic Beanstalk (ap-south-1 Mumbai)

---

## 📁 Project Structure

```
tata_advisor/
├── database.py          ← Car specs + city profiles (data only)
├── tools.py             ← 4 agent tools: weather, cars, fuel, TCO
├── agents.py            ← GeminiAgent, GroqAgent, run_agent()
├── app.py               ← Flask routes + competitor guardrail
├── requirements.txt
├── Procfile             ← gunicorn entry for AWS
├── .env.example
├── static/
│   └── index.html       ← Clean white Tata-style UI
├── .ebextensions/
│   └── 01_flask.config  ← AWS Elastic Beanstalk config
└── .github/
    └── workflows/
        └── deploy.yml   ← GitHub Actions CI/CD pipeline
```

---

## 🖥️ Local Development

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/tata-car-advisor.git
cd tata-car-advisor

# 2. Install
pip install -r requirements.txt

# 3. Set API keys
cp .env.example .env
# Edit .env — add GEMINI_API_KEY and GROQ_API_KEY

# 4. Run
python app.py
# Open http://localhost:5000
```

**Debug individual modules:**
```bash
python database.py   # inspect car data
python tools.py      # test all 4 tools
python agents.py     # test full agent loop
```

---

## 🐙 Step 1 — Push to GitHub

```bash
# Inside tata_advisor/ folder:

git init
git add .
git commit -m "Initial commit — Tata Car Advisor v1"

# Create repo on github.com first, then:
git remote add origin https://github.com/YOUR_USERNAME/tata-car-advisor.git
git branch -M main
git push -u origin main
```

> ⚠️ Never commit `.env` — it's in `.gitignore`. API keys go in GitHub Secrets (step 3).

---

## ☁️ Step 2 — Create AWS Elastic Beanstalk App

### 2a. Open AWS Console
1. Go to **https://console.aws.amazon.com**
2. Search for **Elastic Beanstalk** → Open it
3. Click **Create application**

### 2b. Configure the application
| Field | Value |
|-------|-------|
| Application name | `tata-car-advisor` |
| Platform | **Python** |
| Platform branch | Python 3.11 |
| Application code | Sample application (we'll deploy via GitHub) |

### 2c. Configure environment
| Field | Value |
|-------|-------|
| Environment name | `tata-car-advisor-prod` |
| Domain | auto-generated (e.g. `tata-car-advisor-prod.ap-south-1.elasticbeanstalk.com`) |
| Instance type | `t3.small` (recommended) |
| Region | **ap-south-1** (Mumbai — closest to India) |

### 2d. Add environment variables (your API keys)
In EB Console → your environment → **Configuration** → **Software** → **Environment properties**:

| Key | Value |
|-----|-------|
| `GEMINI_API_KEY` | your key from aistudio.google.com |
| `GROQ_API_KEY` | your key from console.groq.com |

> This is how secrets reach the app on AWS — **never put keys in code or GitHub**.

### 2e. Create IAM user for GitHub Actions
1. Go to **IAM** → **Users** → **Create user**
2. Name: `github-actions-tata`
3. Attach policy: **AWSElasticBeanstalkFullAccess**
4. Go to **Security credentials** → **Create access key**
5. Copy **Access Key ID** and **Secret Access Key** — you'll need these next

---

## 🔑 Step 3 — Add Secrets to GitHub

In your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret Name | Value |
|-------------|-------|
| `AWS_ACCESS_KEY_ID` | IAM access key ID from step 2e |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key from step 2e |

> Gemini/Groq keys go in **AWS EB environment variables** (step 2d), NOT in GitHub Secrets.

---

## 🚀 Step 4 — Deploy

Every `git push` to `main` now triggers the pipeline automatically:

```bash
# Make any change, then:
git add .
git commit -m "your message"
git push origin main
```

**Pipeline steps** (visible in GitHub → Actions tab):
1. ✅ Checkout code
2. ✅ Set up Python 3.11
3. ✅ Install dependencies
4. ✅ Run CI tests (guardrail + database)
5. ✅ Create deployment zip
6. ✅ Deploy to Elastic Beanstalk

**Deployment time:** ~3–5 minutes end to end.

---

## 🌐 After Deployment

Your app will be live at:
```
http://tata-car-advisor-prod.ap-south-1.elasticbeanstalk.com
```

To add a custom domain (optional):
1. Go to **Route 53** → register or import your domain
2. Create an **A record** → Alias → point to your EB environment

---

## 🔍 Monitoring & Logs

```bash
# Install EB CLI
pip install awsebcli

# View live logs
eb logs --environment tata-car-advisor-prod

# SSH into instance
eb ssh tata-car-advisor-prod
```

Or in AWS Console: **Elastic Beanstalk** → your environment → **Logs** → **Request last 100 lines**

---

## 🛡️ Guardrail

The app blocks competitor brand queries before they reach the LLM:

```python
# In app.py — extend this list as needed
COMPETITOR_BRANDS = {
    "maruti", "suzuki", "hyundai", "kia", "honda",
    "mahindra", "toyota", "mg", ...
}
```

Blocked queries get an instant polite refusal. Zero API tokens consumed.

---

## 💰 AWS Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| t3.small EB instance | ~$15–18 |
| Data transfer (India) | ~$2–5 |
| **Total** | **~$17–23/month** |

To pause costs: EB Console → Actions → **Terminate environment** (restartable anytime).

---

*UpGrad KnowledgeHut · AI Engineering Workshop · Agentic AI Module*

# MCAR Platform 🚀
### Multi-Channel Auto Reply & Voice Automation Platform

---

> [!WARNING]
> ### 📢 Upcoming Infrastructure Maintenance Notice
> We will be upgrading critical infrastructure on **May 27th, 6:30 am GMT+5:30** (May 27th, 1:00 am UTC). Follow our status page for real-time updates and recovery progress.

---

## 🌟 About the Project
**MCAR (Multi-Channel Auto Reply & Voice Automation)** is a state-of-the-art conversational AI prototype designed for Chartered Accountancy (CA) firms and business owners. It aggregates customer enquiries arriving from multiple channels (**WhatsApp**, **Instagram**, **Email**, and **Voice Calls**) into a single, unified inbox, where a personalized Google Gemini AI assistant replies instantly on behalf of the business credentials.

---

## 🛠️ Human-Designed Premium Features
1. **Interactive Business Owner Setup:** A frosted glassmorphic configurations panel allowing owners to customize their business name and account numbers (WhatsApp, Instagram, Corporate Email, and Voice lines) on-the-fly.
2. **Unified Lead Routing Visuals:** The Inbox Chat header maps the exact lead-to-business flow:
   `WhatsApp • Customer: +91 98765 43210 ➔ Business: +91 98765 43210`.
3. **100% Indian Context & IST Timezones:** All simulation templates, calendar bookings, and AI responses use Indian Standard Time (IST) and realistic local names/handles (e.g. GST monthly filings, corporate audits).
4. **Custom Abstract SVG Logo:** A sleek geometric vector loop representing flowing communication ribbons and custom human-designed branding.
5. **Real-time Analytics Dashboard:** Direct visualization of Conversion Scores, Sentiment Analysis, and channel distribution.
6. **RAG Knowledge Base & Google Sheets Sync:** Direct upload of pricing PDFs or tax rules to fine-tune AI replies, with simulated sheets lead exports.

---

## 💻 Local Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/MadhuChitikela/mcar-platform.git
cd mcar-platform
```

### 2. Set Up Virtual Environment
```bash
# Create venv
python -m venv venv

# Activate venv
# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Dev Server
```bash
python main.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser!

---

## ☁️ Zero-Configuration Render Deployment

We have included a pre-configured `render.yaml` Blueprint inside the repository.

### How to Fix the "Duplicate GEMINI_API_KEY" Error on Render:
If you are deploying manually as a **Web Service** and connected this repository:
1. Render will **automatically autofill** the environment variables defined in the `render.yaml` blueprint.
2. **Avoid adding `GEMINI_API_KEY` manually twice!** If you see a *"Duplicate key GEMINI_API_KEY is not allowed"* error, simply click the **Trash Can icon 🗑️** next to your manual environment variable row to delete the duplicate.
3. Fill in your Gemini API key inside the remaining, single environment variable input.
4. Click **Deploy Web Service** to start!

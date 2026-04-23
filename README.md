# Articulax

A full-stack web application that simulates real-world speaking scenarios and provides structured, AI-powered feedback to help users improve their communication skills over time.

## What It Does

The user sets a topic, audience, tone, and time limit, then records themselves speaking. Articulax processes the recording through a full pipeline:

1. **Transcription** — audio is sent to the AssemblyAI API and converted to text with word-level timing
2. **Scoring** — a deterministic rubric engine scores the session across 5 dimensions: clarity, confidence, structure, relevance, and vocabulary
3. **AI Feedback** — the Cohere API generates specific, actionable coaching feedback for each dimension
4. **Persistence** — results are saved to a MySQL database across 6 relational tables
5. **Dashboard** — users can track their scores and review past sessions over time

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** MySQL
- **APIs:** AssemblyAI (transcription), Cohere (AI feedback)
- **Auth:** Werkzeug password hashing, Flask sessions

## Project Structure

```
Articulax/
├── app.py                  # Main Flask app — routes, auth, DB logic
├── schema.sql              # MySQL schema
├── requirements.txt
├── services/
│   ├── transcription_service.py   # AssemblyAI integration
│   ├── scoring_service.py         # Rubric scoring engine
│   └── cohere_service.py          # Cohere feedback generation
├── templates/              # HTML pages
└── static/                 # CSS and JS
```

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/zeyd-sheikh/Articulax.git
cd Articulax
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Set up your `.env` file**
```
SECRET_KEY=your_secret_key
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=articulax
ASSEMBLYAI_API_KEY=your_assemblyai_key
COHERE_API_KEY=your_cohere_key  
```

**4. Initialize the database**
```bash
mysql -u your_user -p articulax < schema.sql
```

**5. Run the app**
```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

## API Keys

- AssemblyAI: [assemblyai.com](https://www.assemblyai.com/) — free tier available
- Cohere: [cohere.com](https://cohere.com/) — free trial available

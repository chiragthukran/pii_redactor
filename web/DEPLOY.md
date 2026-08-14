# Deploying to Vercel

## What this is

Same redaction logic as the CLI tool (`redact.py` in the main project),
wrapped in a small Flask API + a plain HTML/JS frontend, structured the way
Vercel expects for a Python backend.

```
pii_redactor_web/
├── api/
│   ├── index.py            <- Flask app, this is the whole backend
│   ├── faker_map.py
│   └── detectors/
│       ├── regex_detectors.py
│       ├── ner_detectors.py
│       └── stoplist.py
├── public/
│   └── index.html           <- frontend, served as a static file
├── requirements.txt
└── vercel.json
```

Vercel auto-detects `api/index.py` as a Python entrypoint because it defines
a module-level `app` (a Flask instance) and sits at one of the filenames
Vercel looks for. Everything in `public/` gets served as static files
automatically, no separate frontend build step needed since this is plain
HTML/CSS/JS rather than a framework.

## Before you deploy - read this

**This is genuinely a bit of an awkward fit for serverless, and it's worth
knowing that going in rather than being surprised by it:**

- spaCy is a heavy dependency. The function bundle (spacy + the language
  model + python-docx + faker) comes in under Vercel's 500MB Python bundle
  limit, so it will deploy fine - but every "cold start" (first request
  after the function has been idle) has to load that model into memory,
  which takes a few seconds on its own, before any actual document
  processing happens.
- Processing the full prospectus (700+ paragraphs) takes real time on top
  of that. `vercel.json` sets `maxDuration: 60` to give it room, but the
  **Hobby (free) plan may cap function duration lower than that regardless**
  - if you're on Hobby and large documents are timing out, that's most
    likely why. Upgrading to Pro raises the ceiling.
- None of this is a bug, it's just what you get putting a spaCy-based tool
  behind a serverless function instead of a normal always-on server. If
  this becomes a real pain point, the more natural fit for this specific
  tool is a small always-on host (Render, Railway, Fly.io, a basic VPS)
  where the model loads once and stays warm - Vercel works, but it's
  optimized for a different kind of workload (short, stateless, frequent
  requests) than "load a 500MB NLP model and chew through a big document."

None of that is a reason not to try Vercel first, since it's free and easy
to set up - just don't be surprised if a very large document is slow or
times out on the first request.

## Steps

1. Push `pii_redactor_web/` to a GitHub repo (a **separate** repo from the
   CLI tool, or a subfolder - your call).

```bash
cd pii_redactor_web
git init
git add .
git commit -m "PII redactor web app"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

2. Go to [vercel.com](https://vercel.com), sign in, click **Add New →
   Project**, and import that GitHub repo.

3. Vercel should auto-detect it as a Python project (because of
   `requirements.txt` + `api/index.py`). Leave the default settings and
   click **Deploy**.

4. First deploy will take a few minutes - it has to `pip install` spacy and
   download the language model wheel. This is normal, it's not stuck.

5. Once deployed, open the URL Vercel gives you. Upload a `.docx`, click
   "Redact document", and you should get a download link plus a
   redaction-count breakdown.

## Testing locally before you deploy

```bash
cd pii_redactor_web
pip install -r requirements.txt
python3 api/index.py
```

This starts a local Flask dev server on `http://localhost:5000`. Open
`public/index.html` directly in a browser (or serve it with any static
server) - the frontend calls `/api/redact` as a relative path, so if you're
opening the HTML file directly rather than through Vercel's routing, you'll
need to either run `vercel dev` (recommended - it replicates Vercel's
routing locally) or point the frontend's fetch URL at
`http://localhost:5000/api/redact` temporarily.

`vercel dev` is the more accurate option:
```bash
npm install -g vercel
vercel dev
```
This runs both the static frontend and the Python function together the
same way Vercel's production routing does.

## If the deploy fails

- **"exceeded the unzipped maximum size"** - check `requirements.txt`
  hasn't picked up something unexpected; run `pip list` in a clean venv
  with just these requirements installed and sanity check nothing huge
  snuck in.
- **"Unable to find any supported Python versions"** - go to Project
  Settings → General and make sure the Node.js version isn't set to
  something that conflicts with Python detection (this has been a known
  quirk on Vercel in the past); usually just re-triggering a deploy after
  checking settings resolves it.
- **Function times out on a real document but works on a small test file**
  - this is the cold-start + processing-time issue described above, not a
    bug in the code specifically. Try increasing `maxDuration` in
    `vercel.json` (Pro plan) or test with a shorter document first to
    confirm the logic itself is fine.

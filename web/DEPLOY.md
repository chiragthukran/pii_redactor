# Deploying to Vercel

## What this is

same redaction logic as the cli tool (`redact.py` in the main project),
just wrapped in a small flask api + plain html/js frontend. structure is
made like how vercel expects a python backend.

```text
pii_redactor_web/
├── api/
│   ├── index.py            <- flask app, this is the backend
│   ├── faker_map.py
│   └── detectors/
│       ├── regex_detectors.py
│       ├── ner_detectors.py
│       └── stoplist.py
├── public/
│   └── index.html           <- frontend, served as static file
├── requirements.txt
└── vercel.json
# VERA Web Application

**Verification Engine for Results & Accountability**

A Streamlit web application for H-EDU that analyzes California education assessment data to identify achievement gaps.

## Features

- **District Dashboard** — OWD analysis, Type 4 flags, charts, CSV export
- **Cross-District Scan** — Statewide Type 4 flag identification
- **LCAP Match-Rate Report** — COE-ready verification reports
- **About VERA** — Methodology and data sources

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Deployment to Render

1. Push this repo to GitHub
2. In Render dashboard: New → Web Service → Connect repo
3. Render auto-detects `render.yaml` and deploys

## Custom Domain Setup

To use `vera.h-edu.solutions`:

1. **Render:** Settings → Custom Domains → Add `vera.h-edu.solutions`
2. **GoDaddy DNS:** Add CNAME record:
   - Name: `vera`
   - Value: `vera-h-edu.onrender.com`

## Data

The app uses `vera_demo.db`, a SQLite database with demo CAASPP and ELPAC data for 10 California school districts.

## Contact

- Website: [h-edu.solutions](https://h-edu.solutions)
- Email: brian@h-edu.solutions

---

*H-EDU / Hallucinations.cloud LLC*

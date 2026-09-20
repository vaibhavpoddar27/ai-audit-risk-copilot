# AI Audit Risk Copilot

**Proof of work:** AI-assisted financial statement risk analysis using synthetic data.

## What it demonstrates

**Financial data → deterministic relationship tests → risk signals → AI reasoning → human review**

Instead of ranking accounts only by percentage movement, the prototype tests relationships such as:

- Trade receivables growth vs revenue growth
- Customer advances vs revenue
- PPE + CWIP vs depreciation
- Supplier advances
- Accrued expenses
- Other operating expenses

Each signal provides:

- why the relationship matters
- potential assertions
- evidence to examine
- plausible benign explanations
- a human review step

## Tech stack

- Python
- Pandas
- Streamlit
- Excel / OpenPyXL
- ChatGPT as the AI reasoning and development copilot

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Responsible use

The included data is completely synthetic. Do **not** upload confidential client information to a personal AI environment. Use only synthetic or explicitly authorised data.

This is a proof of concept, not an audit conclusion engine. Human professional judgement remains responsible for evaluating every signal.

## Why I built it

The project explores how AI can move beyond generic question-answering into structured, domain-specific workflow assistance: identifying relationships in financial data, turning them into reviewable hypotheses, and keeping the final judgement with the professional.

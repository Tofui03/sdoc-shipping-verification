# Shipping document verification

Compares a shipper's Shipping Instruction (SI) with a carrier draft Bill of Lading (BL). The service classifies an inbound email, pulls seven shipment fields out of the attachments, and compares them. Incomplete or ambiguous cases go to a reviewer instead of being marked clean.

Live console: https://tofui03.github.io/sdoc-shipping-verification/

## Architecture

`app.py` is a FastAPI app. The pipeline in `src/pipeline` classifies the email, binds SI and BL roles, extracts fields, and compares them. Comparison of the seven fields (`shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, `gross_weight_kg`) is rule-based. Parsers cover `.txt`, `.docx`, `.xlsx`, and `.pdf`.

`src/llm` has an optional Gemini adapter for steps the rules cannot resolve. The API process does not attach that adapter on its own, so a normal local run stays on the rule path and sends unresolved cases to review.

The operator UI is the React app in `frontend/`. `npm run build` writes the static bundle into `docs/`, which is the directory GitHub Pages publishes.

## Run locally

```bash
git clone https://github.com/Tofui03/sdoc-shipping-verification.git
cd sdoc-shipping-verification

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app:app --reload --port 10000
```

OpenAPI docs: http://localhost:10000/docs

To load synthetic demo cases into the API:

```bash
export SDOC_UAT_DEMO_SEED=1
export SDOC_UAT_SEED_COUNT=250   # optional; without this, a local run seeds 4 cases
uvicorn app:app --reload --port 10000
```

After a frontend production build, the console is at http://localhost:10000/cases. For UI development:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the UI on port 5173 and proxies `/api` to http://localhost:10000. `frontend/.env.example` lists the proxy settings. If you use Gemini, put `GEMINI_API_KEY` in a gitignored `.env` at the repo root.

## Tests

```bash
pytest -q
cd frontend && npm test && npm run build
```

## Stack

Python 3.12, FastAPI, Pydantic v2, pytest. React 18, TypeScript, Vite, Tailwind, Vitest.

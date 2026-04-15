# Claim Processing Pipeline

FastAPI service that processes claim PDFs using a LangGraph workflow:

`START -> Segregator Agent -> [ID Agent, Discharge Summary Agent, Itemized Bill Agent] -> Aggregator -> END`

## What it does

- Accepts a PDF and `claim_id` on `POST /api/process`
- Segregates pages into 9 document types
- Routes only relevant pages to the 3 extraction agents
- Aggregates extracted data into one JSON response

## Tech

- FastAPI
- LangGraph
- OpenAI via `langchain-openai`
- PyPDF

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
PDF_PASSWORD=
```

`OPENAI_API_KEY` is optional. If it is missing, the service uses heuristic fallback logic so the API still runs locally, but the segregator is no longer LLM-backed.

For scanned or image-only PDFs, OCR fallback is enabled automatically when `tesseract` is installed on the machine and these Python packages are present:

```bash
pip install pytesseract Pillow
```

Optional `.env` toggle:

```env
ENABLE_OCR=true
```

## Run

```bash
uvicorn app.main:app --reload
```

## API

### `POST /api/process`

Multipart form-data:

- `claim_id`: string
- `file`: PDF

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/process \
  -F "claim_id=CLM-001" \
  -F "file=@final_image_protected.pdf;type=application/pdf"
```

Example response shape:

```json
{
  "claim_id": "CLM-001",
  "classifications": [
    {
      "page_number": 1,
      "document_type": "identity_document",
      "reason": "Contains patient identity and policy information."
    }
  ],
  "extracted_data": {
    "identity_document": {
      "patient_name": "John Doe",
      "date_of_birth": "01/01/1980",
      "id_numbers": ["ABC123456"],
      "policy_number": "POL-789",
      "insurer_name": "Example Insurance"
    },
    "discharge_summary": {
      "diagnosis": "Acute appendicitis",
      "admission_date": "02/01/2026",
      "discharge_date": "05/01/2026",
      "physician_name": "Dr. Smith",
      "hospital_name": "Example Hospital"
    },
    "itemized_bill": {
      "items": [
        {
          "description": "Room charges",
          "quantity": 1,
          "unit_price": 5000,
          "amount": 5000
        }
      ],
      "total_amount": 5000,
      "currency": "INR"
    }
  }
}
```

## Workflow

### 1. Segregator Agent

- Reads page text from the uploaded PDF
- Classifies every page into one of:
  - `claim_forms`
  - `cheque_or_bank_details`
  - `identity_document`
  - `itemized_bill`
  - `discharge_summary`
  - `prescription`
  - `investigation_report`
  - `cash_receipt`
  - `other`
- Builds per-document page lists
- Produces mini PDFs for the 3 extraction agents so they do not receive the whole file

### 2. Extraction Agents

- `ID Agent`: patient identity, DOB, ID numbers, policy details
- `Discharge Summary Agent`: diagnosis, admission/discharge dates, physician, hospital
- `Itemized Bill Agent`: bill items, costs, total amount

Each agent only reads the text from its assigned pages.

### 3. Aggregator

- Merges classifications and extraction outputs
- Returns one final JSON response

## Files

- [app/main.py](/Users/asmijafar/claim-Processing_pipeline/app/main.py)
- [app/graph.py](/Users/asmijafar/claim-Processing_pipeline/app/graph.py)
- [app/pdf_utils.py](/Users/asmijafar/claim-Processing_pipeline/app/pdf_utils.py)
- [app/llm.py](/Users/asmijafar/claim-Processing_pipeline/app/llm.py)
- [app/schemas.py](/Users/asmijafar/claim-Processing_pipeline/app/schemas.py)

## Notes

- If the sample PDF is password protected, set `PDF_PASSWORD` in `.env`.
- Image-only PDFs require OCR. This project now falls back to `tesseract` OCR when embedded PDF text is missing.
- If OCR packages are not installed, image-only pages will still be classified as `other` with a reason explaining that no text could be extracted.

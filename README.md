# Claim Processing Pipeline

FastAPI service that processes claim PDFs using a LangGraph workflow:

`START -> Segregator Agent -> [ID Agent, Discharge Summary Agent, Itemized Bill Agent] -> Aggregator -> END`

## What it does

- Accepts a PDF and `claim_id` on `POST /api/process`
- Segregates pages into 9 document types
- Routes only relevant pages to the 3 extraction agents
- Aggregates extracted data into one JSON response

### JSON Response while running 
`curl -X POST http://127.0.0.1:8000/api/process -F "claim_id=CLM-001" -F "file=@final_image_protected.pdf;type=application/pdf"`
```json
{
  "claim_id": "CLM-001",
  "classifications": [
    {
      "page_number": 1,
      "document_type": "claim_forms",
      "reason": "This page contains a medical claim form with patient information and claim details."
    },
    {
      "page_number": 2,
      "document_type": "cheque_or_bank_details",
      "reason": "This page includes bank details and cheque information."
    },
    {
      "page_number": 3,
      "document_type": "identity_document",
      "reason": "This page is a government-issued ID card."
    },
    {
      "page_number": 4,
      "document_type": "discharge_summary",
      "reason": "This page provides a discharge summary detailing the patient's hospital stay."
    },
    {
      "page_number": 5,
      "document_type": "prescription",
      "reason": "This page contains a prescription issued by a doctor."
    },
    {
      "page_number": 6,
      "document_type": "investigation_report",
      "reason": "This page is a laboratory report detailing blood test results."
    },
    {
      "page_number": 7,
      "document_type": "cash_receipt",
      "reason": "This page is a cash receipt for payments made at the medical center."
    },
    {
      "page_number": 8,
      "document_type": "other",
      "reason": "This page is a patient registration form, not fitting other categories."
    },
    {
      "page_number": 9,
      "document_type": "itemized_bill",
      "reason": "This page is an itemized hospital bill listing charges for services."
    },
    {
      "page_number": 10,
      "document_type": "itemized_bill",
      "reason": "This page is a pharmacy and outpatient bill detailing medication charges."
    },
    {
      "page_number": 11,
      "document_type": "investigation_report",
      "reason": "This page is a laboratory report for a metabolic panel."
    },
    {
      "page_number": 12,
      "document_type": "investigation_report",
      "reason": "This page is a laboratory report for a lipid panel and thyroid function tests."
    },
    {
      "page_number": 13,
      "document_type": "other",
      "reason": "This page is an informed consent form for a medical procedure."
    },
    {
      "page_number": 14,
      "document_type": "other",
      "reason": "This page is an appointment confirmation letter."
    },
    {
      "page_number": 15,
      "document_type": "other",
      "reason": "This page is an insurance verification form."
    },
    {
      "page_number": 16,
      "document_type": "other",
      "reason": "This page is a medical history questionnaire."
    },
    {
      "page_number": 17,
      "document_type": "other",
      "reason": "This page is a referral letter from one doctor to another."
    },
    {
      "page_number": 18,
      "document_type": "other",
      "reason": "This page continues the referral letter with treatment details."
    }
  ],
  "extracted_data": {
    "identity_document": {
      "patient_name": "John Michael Smith",
      "date_of_birth": "March 15, 1985",
      "id_numbers": [
        "CLM-2024-789456",
        "POL-987654321",
        "1-555-0123",
        "ICD-10"
      ],
      "policy_number": "POL-987654321",
      "insurer_name": "HealthCare Insurance Company"
    },
    "discharge_summary": {
      "diagnosis": "Community Acquired Pneumonia (CAP)",
      "admission_date": "January 20, 2025",
      "discharge_date": "January 25, 2025",
      "physician_name": "Dr. Sarah Johnson, MD",
      "hospital_name": "CITY MEDICAL CENTER"
    },
    "itemized_bill": {
      "items": [
        {
          "description": "Room Charges - Semi-Private (5 days)",
          "quantity": 5,
          "unit_price": 200,
          "amount": 1000
        },
        {
          "description": "Admission Fee",
          "quantity": 1,
          "unit_price": 150,
          "amount": 150
        },
        {
          "description": "Emergency Room Services",
          "quantity": 1,
          "unit_price": 500,
          "amount": 500
        },
        {
          "description": "Physician Consultation - Dr. Sarah Johnson",
          "quantity": 5,
          "unit_price": 150,
          "amount": 750
        },
        {
          "description": "Chest X-Ray",
          "quantity": 2,
          "unit_price": 120,
          "amount": 240
        },
        {
          "description": "CT Scan - Chest",
          "quantity": 1,
          "unit_price": 800,
          "amount": 800
        },
        {
          "description": "Complete Blood Count (CBC)",
          "quantity": 3,
          "unit_price": 45,
          "amount": 135
        },
        {
          "description": "Blood Culture Test",
          "quantity": 2,
          "unit_price": 80,
          "amount": 160
        },
        {
          "description": "Arterial Blood Gas Analysis",
          "quantity": 1,
          "unit_price": 95,
          "amount": 95
        },
        {
          "description": "IV Fluids - Normal Saline",
          "quantity": 10,
          "unit_price": 25,
          "amount": 250
        },
        {
          "description": "Injection - Ceftriaxone 1g",
          "quantity": 5,
          "unit_price": 30,
          "amount": 150
        },
        {
          "description": "Injection - Paracetamol",
          "quantity": 6,
          "unit_price": 8,
          "amount": 48
        },
        {
          "description": "Nebulization Treatment",
          "quantity": 4,
          "unit_price": 35,
          "amount": 140
        },
        {
          "description": "Oxygen Therapy (per hour)",
          "quantity": 48,
          "unit_price": 5,
          "amount": 240
        },
        {
          "description": "Nursing Care (per day)",
          "quantity": 5,
          "unit_price": 100,
          "amount": 500
        },
        {
          "description": "ICU Monitoring Equipment",
          "quantity": 2,
          "unit_price": 200,
          "amount": 400
        },
        {
          "description": "Physiotherapy Session",
          "quantity": 3,
          "unit_price": 60,
          "amount": 180
        },
        {
          "description": "Medical Supplies & Consumables",
          "quantity": 1,
          "unit_price": 250,
          "amount": 250
        },
        {
          "description": "Laboratory Processing Fee",
          "quantity": 1,
          "unit_price": 75,
          "amount": 75
        },
        {
          "description": "Pharmacy Dispensing Fee",
          "quantity": 1,
          "unit_price": 50,
          "amount": 50
        },
        {
          "description": "Amoxicillin 500mg Capsules",
          "quantity": 21,
          "unit_price": 1.5,
          "amount": 31.5
        },
        {
          "description": "Acetaminophen 500mg Tablets",
          "quantity": 20,
          "unit_price": 0.8,
          "amount": 16
        },
        {
          "description": "Cetirizine 10mg Tablets",
          "quantity": 0,
          "unit_price": 0.9,
          "amount": 0
        },
        {
          "description": "Omeprazole 20mg Capsules",
          "quantity": 4,
          "unit_price": 1.2,
          "amount": 16.8
        },
        {
          "description": "Albuterol Inhaler",
          "quantity": 1,
          "unit_price": 35,
          "amount": 35
        },
        {
          "description": "Vitamin D3 1000 IU",
          "quantity": 30,
          "unit_price": 0.4,
          "amount": 12
        },
        {
          "description": "Probiotic Capsules",
          "quantity": 30,
          "unit_price": 0.85,
          "amount": 25.5
        },
        {
          "description": "Saline Nasal Spray",
          "quantity": 1,
          "unit_price": 8.5,
          "amount": 8.5
        },
        {
          "description": "Antiseptic Mouthwash 250ml",
          "quantity": 1,
          "unit_price": 12,
          "amount": 12
        },
        {
          "description": "Digital Thermometer",
          "quantity": 1,
          "unit_price": 15,
          "amount": 15
        },
        {
          "description": "Medication Counseling",
          "quantity": 1,
          "unit_price": 25,
          "amount": 25
        },
        {
          "description": "Home Delivery Service",
          "quantity": 1,
          "unit_price": 10,
          "amount": 10
        }
      ],
      "total_amount": 6418.65,
      "currency": "USD"
    }
  }
}
```

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

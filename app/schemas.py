from typing import Literal

from pydantic import BaseModel, Field


DocType = Literal[
    "claim_forms",
    "cheque_or_bank_details",
    "identity_document",
    "itemized_bill",
    "discharge_summary",
    "prescription",
    "investigation_report",
    "cash_receipt",
    "other",
]


class PageClassification(BaseModel):
    page_number: int = Field(ge=1)
    document_type: DocType
    reason: str


class IdentityExtraction(BaseModel):
    patient_name: str | None = None
    date_of_birth: str | None = None
    id_numbers: list[str] = Field(default_factory=list)
    policy_number: str | None = None
    insurer_name: str | None = None


class DischargeExtraction(BaseModel):
    diagnosis: str | None = None
    admission_date: str | None = None
    discharge_date: str | None = None
    physician_name: str | None = None
    hospital_name: str | None = None


class BillItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


class ItemizedBillExtraction(BaseModel):
    items: list[BillItem] = Field(default_factory=list)
    total_amount: float | None = None
    currency: str | None = None


class AggregatedClaimResult(BaseModel):
    claim_id: str
    classifications: list[PageClassification]
    extracted_data: dict[str, object]

from __future__ import annotations

import re
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.llm import ainvoke_structured, extract_money_values, safe_json_dumps
from app.pdf_utils import PDFPage, extract_selected_pages, load_pdf_pages
from app.schemas import (
    AggregatedClaimResult,
    BillItem,
    DocType,
    DischargeExtraction,
    IdentityExtraction,
    ItemizedBillExtraction,
    PageClassification,
)


def _merge_lists(left: list[Any] | None, right: list[Any] | None) -> list[Any]:
    return (left or []) + (right or [])


class GraphState(TypedDict, total=False):
    claim_id: str
    file_bytes: bytes
    pages: list[PDFPage]
    page_classifications: Annotated[list[PageClassification], _merge_lists]
    segregated_pages: dict[str, list[int]]
    extracted_page_pdfs: dict[str, bytes]
    id_result: dict[str, Any]
    discharge_result: dict[str, Any]
    itemized_bill_result: dict[str, Any]
    final_result: dict[str, Any]


async def _classify_with_llm(pages: list[PDFPage]) -> list[PageClassification] | None:
    from pydantic import BaseModel, Field

    class PageClassificationResponse(BaseModel):
        classifications: list[PageClassification] = Field(default_factory=list)

    system_prompt = (
        "You classify medical claim PDF pages. "
        "Use exactly one of these document types per page: "
        "claim_forms, cheque_or_bank_details, identity_document, itemized_bill, "
        "discharge_summary, prescription, investigation_report, cash_receipt, other."
    )
    blank_page_classifications = {
        page.page_number: PageClassification(
            page_number=page.page_number,
            document_type="other",
            reason=(
                "No text could be extracted from the page. "
                "Install OCR dependencies or verify the PDF is not image-only."
            ),
        )
        for page in pages
        if not page.text.strip()
    }
    pages_with_text = [page for page in pages if page.text.strip()]
    if not pages_with_text:
        return [blank_page_classifications[page.page_number] for page in pages]

    page_payload = [
        {"page_number": page.page_number, "text": page.text[:4000]}
        for page in pages_with_text
    ]
    user_prompt = (
        "Classify each page and provide a short reason.\n"
        f"{safe_json_dumps(page_payload)}"
    )
    response = await ainvoke_structured(PageClassificationResponse, system_prompt, user_prompt)
    if response is None:
        return None
    combined = {item.page_number: item for item in response.classifications}
    combined.update(blank_page_classifications)
    if len(combined) != len(pages):
        return None
    return [combined[page.page_number] for page in pages]


def _heuristic_doc_type(text: str) -> DocType:
    lower = text.lower()
    if any(
        token in lower
        for token in [
            "claim form",
            "medical claim form",
            "insurance verification",
            "verification details",
        ]
    ):
        return "claim_forms"
    if any(token in lower for token in ["aadhaar", "passport", "identity", "dob", "policy no", "member id"]):
        return "identity_document"
    if any(token in lower for token in ["discharge summary", "final diagnosis", "date of admission", "date of discharge"]):
        return "discharge_summary"
    if any(token in lower for token in ["itemized bill", "bill details", "qty", "rate", "amount", "particulars"]):
        return "itemized_bill"
    if any(token in lower for token in ["claimant", "tpa"]):
        return "claim_forms"
    if any(token in lower for token in ["cancelled cheque", "ifsc", "account number", "bank"]):
        return "cheque_or_bank_details"
    if any(token in lower for token in ["prescription", "rx", "tablet", "capsule"]):
        return "prescription"
    if any(token in lower for token in ["investigation", "lab report", "test result", "radiology"]):
        return "investigation_report"
    if any(token in lower for token in ["cash receipt", "receipt no", "payment received"]):
        return "cash_receipt"
    return "other"


def _heuristic_classifications(pages: list[PDFPage]) -> list[PageClassification]:
    classifications: list[PageClassification] = []
    for page in pages:
        document_type = _heuristic_doc_type(page.text)
        if page.text.strip():
            reason = (
                "Heuristic fallback based on page text keywords."
                if page.text_source == "embedded"
                else "Heuristic fallback based on OCR text extracted from page images."
            )
        else:
            reason = (
                "No text could be extracted from the page. "
                "Install OCR dependencies or verify the PDF is not image-only."
            )
        classifications.append(
            PageClassification(
                page_number=page.page_number,
                document_type=document_type,
                reason=reason,
            )
        )
    return classifications


def _page_text_by_numbers(pages: list[PDFPage], page_numbers: list[int]) -> str:
    page_number_set = set(page_numbers)
    selected = [page for page in pages if page.page_number in page_number_set]
    return "\n\n".join(
        f"Page {page.page_number}\n{page.text[:5000]}" for page in selected if page.text
    )


async def segregator_agent(state: GraphState) -> GraphState:
    pages = load_pdf_pages(state["file_bytes"])
    classifications = await _classify_with_llm(pages)
    if classifications is None or len(classifications) != len(pages):
        classifications = _heuristic_classifications(pages)

    segregated_pages: dict[str, list[int]] = {
        "claim_forms": [],
        "cheque_or_bank_details": [],
        "identity_document": [],
        "itemized_bill": [],
        "discharge_summary": [],
        "prescription": [],
        "investigation_report": [],
        "cash_receipt": [],
        "other": [],
    }
    for item in classifications:
        segregated_pages[item.document_type].append(item.page_number)

    extracted_page_pdfs = {
        "identity_document": extract_selected_pages(
            state["file_bytes"], segregated_pages["identity_document"]
        ),
        "discharge_summary": extract_selected_pages(
            state["file_bytes"], segregated_pages["discharge_summary"]
        ),
        "itemized_bill": extract_selected_pages(
            state["file_bytes"], segregated_pages["itemized_bill"]
        ),
    }

    return {
        "pages": pages,
        "page_classifications": classifications,
        "segregated_pages": segregated_pages,
        "extracted_page_pdfs": extracted_page_pdfs,
    }


def _regex_first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


async def id_agent(state: GraphState) -> GraphState:
    page_numbers = sorted(
        set(state["segregated_pages"].get("identity_document", []))
        | set(state["segregated_pages"].get("claim_forms", []))
    )
    text = _page_text_by_numbers(state["pages"], page_numbers)
    if not text:
        return {"id_result": IdentityExtraction().model_dump()}

    class IdentityResponse(IdentityExtraction):
        pass

    system_prompt = (
        "Extract identity and policy details from claim identity pages. "
        "Return only values supported by the provided text."
    )
    user_prompt = text[:12000]
    raw_id_numbers = re.findall(r"\b[A-Z0-9][A-Z0-9\-\/]{5,19}\b", text)
    id_numbers: list[str] = []
    for value in raw_id_numbers:
        if not any(char.isdigit() for char in value):
            continue
        if value not in id_numbers:
            id_numbers.append(value)
    fallback = IdentityExtraction(
        patient_name=_regex_first(
            r"(?:patient name|name|patient)\s*[:\-]\s*([A-Za-z .]+?)(?=\s*(?:date of birth|dob|date|patient id|policy number|contact|email)\s*[:\-]|$)",
            text,
        ),
        date_of_birth=_regex_first(
            r"(?:dob|date of birth)\s*[:\-]\s*([A-Za-z]+ \d{1,2}, \d{4}|[0-9\/\-]+)",
            text,
        ),
        id_numbers=id_numbers[:5],
        policy_number=_regex_first(r"(?:policy (?:number|no))\s*[:\-]?\s*([A-Z0-9\-\/]+)", text),
        insurer_name=_regex_first(
            r"(?:insurer|insurance company|insurance provider)\s*[:\-]\s*([A-Za-z0-9 .&]+)",
            text,
        ),
    )

    response = await ainvoke_structured(IdentityResponse, system_prompt, user_prompt)
    if response is not None:
        merged = response.model_copy(
            update={
                "patient_name": response.patient_name or fallback.patient_name,
                "date_of_birth": response.date_of_birth or fallback.date_of_birth,
                "policy_number": response.policy_number or fallback.policy_number,
                "insurer_name": response.insurer_name or fallback.insurer_name,
                "id_numbers": response.id_numbers or fallback.id_numbers,
            }
        )
        return {"id_result": merged.model_dump()}

    return {"id_result": fallback.model_dump()}


async def discharge_summary_agent(state: GraphState) -> GraphState:
    page_numbers = state["segregated_pages"].get("discharge_summary", [])
    text = _page_text_by_numbers(state["pages"], page_numbers)
    if not text:
        return {"discharge_result": DischargeExtraction().model_dump()}

    class DischargeResponse(DischargeExtraction):
        pass

    system_prompt = (
        "Extract discharge summary data from the supplied pages. "
        "Capture diagnosis, admission/discharge dates, physician, and hospital."
    )
    response = await ainvoke_structured(DischargeResponse, system_prompt, text[:12000])
    if response is not None:
        return {"discharge_result": response.model_dump()}

    fallback = DischargeExtraction(
        diagnosis=_regex_first(r"(?:diagnosis|final diagnosis)\s*[:\-]\s*(.+)", text),
        admission_date=_regex_first(r"(?:date of admission|admission date)\s*[:\-]\s*([0-9\/\-]+)", text),
        discharge_date=_regex_first(r"(?:date of discharge|discharge date)\s*[:\-]\s*([0-9\/\-]+)", text),
        physician_name=_regex_first(r"(?:consultant|doctor|physician)\s*[:\-]\s*([A-Za-z .]+)", text),
        hospital_name=_regex_first(r"(?:hospital|facility)\s*[:\-]\s*([A-Za-z0-9 .&]+)", text),
    )
    return {"discharge_result": fallback.model_dump()}


async def itemized_bill_agent(state: GraphState) -> GraphState:
    page_numbers = state["segregated_pages"].get("itemized_bill", [])
    text = _page_text_by_numbers(state["pages"], page_numbers)
    if not text:
        return {"itemized_bill_result": ItemizedBillExtraction().model_dump()}

    class ItemizedResponse(ItemizedBillExtraction):
        pass

    system_prompt = (
        "Extract every bill line item you can identify from these hospital bill pages. "
        "Compute the final total_amount from the items or explicit total shown."
    )
    response = await ainvoke_structured(ItemizedResponse, system_prompt, text[:16000])
    if response is not None:
        return {"itemized_bill_result": response.model_dump()}

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items: list[BillItem] = []
    for line in lines:
        values = extract_money_values(line)
        if values and any(ch.isalpha() for ch in line):
            amount = values[-1]
            description = re.sub(r"\s+", " ", re.sub(r"(?:Rs\.?|INR)?\s*[0-9,]+(?:\.[0-9]{1,2})?", "", line)).strip(" -:")
            if description:
                items.append(BillItem(description=description[:120], amount=amount))

    total_candidates = extract_money_values(text)
    fallback = ItemizedBillExtraction(
        items=items[:50],
        total_amount=max(total_candidates) if total_candidates else None,
        currency="INR" if ("rs" in text.lower() or "inr" in text.lower()) else None,
    )
    return {"itemized_bill_result": fallback.model_dump()}


async def aggregator(state: GraphState) -> GraphState:
    result = AggregatedClaimResult(
        claim_id=state["claim_id"],
        classifications=state["page_classifications"],
        extracted_data={
            "identity_document": state.get("id_result", {}),
            "discharge_summary": state.get("discharge_result", {}),
            "itemized_bill": state.get("itemized_bill_result", {}),
        },
    )
    return {"final_result": result.model_dump()}


def build_claim_graph():
    graph = StateGraph(GraphState)
    graph.add_node("segregator_agent", segregator_agent)
    graph.add_node("id_agent", id_agent)
    graph.add_node("discharge_summary_agent", discharge_summary_agent)
    graph.add_node("itemized_bill_agent", itemized_bill_agent)
    graph.add_node("aggregator", aggregator)

    graph.add_edge(START, "segregator_agent")
    graph.add_edge("segregator_agent", "id_agent")
    graph.add_edge("segregator_agent", "discharge_summary_agent")
    graph.add_edge("segregator_agent", "itemized_bill_agent")
    graph.add_edge("id_agent", "aggregator")
    graph.add_edge("discharge_summary_agent", "aggregator")
    graph.add_edge("itemized_bill_agent", "aggregator")
    graph.add_edge("aggregator", END)

    return graph.compile()

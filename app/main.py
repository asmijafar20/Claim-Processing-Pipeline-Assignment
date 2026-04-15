from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.graph import build_claim_graph

app = FastAPI(title="Claim Processing Pipeline", version="0.1.0")
claim_graph = build_claim_graph()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/process")
async def process_claim(
    claim_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = await claim_graph.ainvoke(
            {"claim_id": claim_id, "file_bytes": file_bytes}
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc

    return result["final_result"]

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import settings


def get_chat_model() -> ChatOpenAI | None:
    if not settings.openai_api_key:
        return None
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


async def ainvoke_structured(
    schema: type[BaseModel], system_prompt: str, user_prompt: str
) -> BaseModel | None:
    model = get_chat_model()
    if model is None:
        return None

    structured_model = model.with_structured_output(schema)
    return await structured_model.ainvoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    )


def extract_money_values(text: str) -> list[float]:
    values: list[float] = []
    for match in re.findall(r"(?:Rs\.?|INR)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", text):
        try:
            values.append(float(match.replace(",", "")))
        except ValueError:
            continue
    return values


def safe_json_dumps(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True)

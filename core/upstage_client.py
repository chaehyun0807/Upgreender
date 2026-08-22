"""Thin wrapper around Upstage's Document Parse and Chat Completions APIs."""
from __future__ import annotations

import json

import requests

from core.config import CHAT_COMPLETIONS_URL, DOCUMENT_PARSE_URL, UPSTAGE_API_KEY, UPSTAGE_CHAT_MODEL


class UpstageError(RuntimeError):
    pass


def _auth_headers() -> dict:
    if not UPSTAGE_API_KEY:
        raise UpstageError("UPSTAGE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return {"Authorization": f"Bearer {UPSTAGE_API_KEY}"}


def parse_document(file_bytes: bytes, filename: str) -> str:
    """Send a file (pdf/image/docx/xlsx/pptx/...) to Upstage Document Parse and
    return the parsed document as markdown text."""
    response = requests.post(
        DOCUMENT_PARSE_URL,
        headers=_auth_headers(),
        files={"document": (filename, file_bytes)},
        data={
            "model": "document-parse",
            "output_formats": json.dumps(["markdown"]),
            "ocr": "auto",
        },
        timeout=120,
    )
    if response.status_code != 200:
        raise UpstageError(f"Document Parse 실패 ({response.status_code}): {response.text[:500]}")
    payload = response.json()
    markdown = payload.get("content", {}).get("markdown")
    if not markdown:
        markdown = "\n\n".join(
            el.get("content", {}).get("markdown", "") for el in payload.get("elements", [])
        )
    return markdown.strip()


def chat_json(system_prompt: str, user_content: str, json_schema: dict, schema_name: str) -> dict:
    """Call Solar chat completions with a strict JSON schema and return the parsed dict."""
    body = {
        "model": UPSTAGE_CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": json_schema,
            },
        },
    }
    headers = {**_auth_headers(), "Content-Type": "application/json"}

    last_error: Exception | None = None
    for attempt in range(2):
        response = requests.post(CHAT_COMPLETIONS_URL, headers=headers, json=body, timeout=120)
        if response.status_code != 200:
            raise UpstageError(f"Chat Completions 실패 ({response.status_code}): {response.text[:500]}")
        content = response.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            last_error = exc
            body["messages"].append(
                {
                    "role": "user",
                    "content": "이전 응답이 올바른 JSON이 아니었습니다. JSON 스키마를 정확히 지키는 JSON만 출력하세요.",
                }
            )
    raise UpstageError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {last_error}")

"""Thin wrapper around Upstage's Document Parse and Chat Completions APIs."""
from __future__ import annotations

import json
import time

import requests

from core.config import (
    AGENT_FILES_URL,
    AGENT_RESPONSES_URL,
    CHAT_COMPLETIONS_URL,
    DOCUMENT_PARSE_URL,
    UPSTAGE_AGENT_ID,
    UPSTAGE_API_KEY,
    UPSTAGE_CHAT_MODEL,
)


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


def upload_agent_file(file_bytes: bytes, filename: str) -> str:
    """1단계: Studio 에이전트(/v2/responses)에서 참조할 수 있도록 파일을 업로드하고 file_id를 반환한다."""
    response = requests.post(
        AGENT_FILES_URL,
        headers=_auth_headers(),
        files={"file": (filename, file_bytes)},
        data={"purpose": "user_data"},
        timeout=120,
    )
    if response.status_code != 200:
        raise UpstageError(f"파일 업로드 실패 ({response.status_code}): {response.text[:500]}")
    payload = response.json()
    file_id = payload.get("id") or payload.get("file_id")
    if not file_id:
        raise UpstageError(f"파일 업로드 응답에서 file_id를 찾지 못했습니다: {response.text[:500]}")
    return file_id


def call_agent(
    file_bytes: bytes,
    filename: str,
    agent_id: str | None = None,
    poll_interval: float = 2.0,
    poll_timeout: float = 120.0,
) -> dict:
    """2단계: Studio에서 만든 Parse->Classify->Extract->Instruct 에이전트에 문서를 보내고
    /v2/responses의 최종(완료된) JSON 응답을 반환한다.

    /v2/responses는 비동기 작업으로 동작한다 — 최초 응답은 status="in_progress"에
    output=[]인 채로 즉시 돌아오므로, status가 "completed"가 될 때까지
    GET /v2/responses/{id}를 폴링한다."""
    file_id = upload_agent_file(file_bytes, filename)
    body = {
        "model": agent_id or UPSTAGE_AGENT_ID,
        "include": ["last"],
        "input": [{"role": "user", "content": [{"type": "input_file", "file_id": file_id}]}],
    }
    headers = {**_auth_headers(), "Content-Type": "application/json"}
    response = requests.post(AGENT_RESPONSES_URL, headers=headers, json=body, timeout=180)
    if response.status_code != 200:
        raise UpstageError(f"에이전트 호출 실패 ({response.status_code}): {response.text[:500]}")
    result = response.json()

    job_id = result.get("id")
    elapsed = 0.0
    while result.get("status") == "in_progress" and job_id and elapsed < poll_timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval
        poll_response = requests.get(f"{AGENT_RESPONSES_URL}/{job_id}", headers=headers, timeout=30)
        if poll_response.status_code != 200:
            raise UpstageError(f"에이전트 상태 조회 실패 ({poll_response.status_code}): {poll_response.text[:500]}")
        result = poll_response.json()

    status = result.get("status")
    if status == "in_progress":
        raise UpstageError(f"에이전트 응답이 {poll_timeout}초 안에 완료되지 않았습니다 (job_id={job_id}).")
    if status in ("failed", "cancelled", "incomplete"):
        raise UpstageError(f"에이전트 실행 실패 (status={status}): {json.dumps(result, ensure_ascii=False)[:500]}")
    return result


def parse_agent_output(response_json: dict) -> tuple[str, dict]:
    """완료된 /v2/responses 응답에서 (분류된 브랜치 이름, 추출된 JSON dict) 하나를 찾아 반환한다.
    실제 응답 구조: output[].content[].text 안에 JSON 문자열이 들어있고,
    output[].model에 어떤 Extract 브랜치("Information Extract - 추출-N")로 라우팅됐는지 담겨 있다."""
    for item in response_json.get("output", []):
        if item.get("type") != "message":
            continue
        branch = item.get("model") or ""
        for part in item.get("content", []):
            if part.get("type") == "output_text" and part.get("text"):
                try:
                    return branch, json.loads(part["text"])
                except json.JSONDecodeError:
                    continue
    raise UpstageError("에이전트 응답에서 추출된 JSON을 찾지 못했습니다.")


def extract_agent_output_text(response_json: dict) -> str:
    """/v2/responses 응답에서 에이전트의 최종 출력 텍스트를 최대한 찾아내고,
    구조를 모르면 원본 JSON 문자열을 그대로 반환한다 (응답 스키마가 확정되지 않았으므로
    방어적으로 동작)."""
    output = response_json.get("output") or response_json.get("outputs")
    if isinstance(output, list):
        for item in reversed(output):
            content = item.get("content") if isinstance(item, dict) else None
            if isinstance(content, list):
                for part in content:
                    text = part.get("text") if isinstance(part, dict) else None
                    if text:
                        return text
            elif isinstance(content, str) and content:
                return content
    return json.dumps(response_json, ensure_ascii=False, indent=2)

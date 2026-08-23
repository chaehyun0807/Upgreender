import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "app.db"
SAMPLE_SYLLABI_PATH = DATA_DIR / "sample_syllabi.json"
SAMPLE_PROFILE_PATH = DATA_DIR / "sample_profile.json"

load_dotenv(ROOT_DIR / ".env")

UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY", "").strip()
UPSTAGE_CHAT_MODEL = os.environ.get("UPSTAGE_CHAT_MODEL", "solar-pro2").strip()

DOCUMENT_PARSE_URL = "https://api.upstage.ai/v1/document-digitization"
CHAT_COMPLETIONS_URL = "https://api.upstage.ai/v1/chat/completions"

# Studio에서 만든 Parse->Classify->Extract->Instruct 에이전트 (agent builder UI에서 생성, API로는 생성 불가)
UPSTAGE_AGENT_ID = os.environ.get("UPSTAGE_AGENT_ID", "agt_mLkaQNZLzMMeSLEH89XDFU").strip()
AGENT_FILES_URL = "https://api.upstage.ai/v2/files"
AGENT_RESPONSES_URL = "https://api.upstage.ai/v2/responses"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

KAKAO_JS_KEY = os.environ.get("KAKAO_JS_KEY", "").strip()
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "").strip()

KAKAO_KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def has_upstage_key() -> bool:
    return bool(UPSTAGE_API_KEY)


def has_kakao_keys() -> bool:
    return bool(KAKAO_JS_KEY and KAKAO_REST_API_KEY)


def has_discord_webhook() -> bool:
    return bool(DISCORD_WEBHOOK_URL)

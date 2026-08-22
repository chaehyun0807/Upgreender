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

KAKAO_JS_KEY = os.environ.get("KAKAO_JS_KEY", "").strip()
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "").strip()

KAKAO_KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def has_upstage_key() -> bool:
    return bool(UPSTAGE_API_KEY)


def has_kakao_keys() -> bool:
    return bool(KAKAO_JS_KEY and KAKAO_REST_API_KEY)

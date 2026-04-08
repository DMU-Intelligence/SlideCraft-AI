import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    app_name: str

    # LLM 모드: "mock" | "openai" | "gemini"
    llm_mode: str

    # OpenAI 호환 설정
    openai_base_url: str
    openai_api_key: str | None
    openai_model: str

    # Gemini 설정
    gemini_api_key: str | None
    gemini_model: str

    # 저장소
    project_repo_mode: str
    project_repo_path: str

    upload_dir: str


def _getenv(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None and value != "" else default


def load_settings() -> Settings:
    return Settings(
        app_name=_getenv("APP_NAME", "SlideCraft AI"),
        llm_mode=_getenv("LLM_MODE", "mock").lower(),

        openai_base_url=_getenv("OPENAI_BASE_URL", "https://api.openai.com"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=_getenv("OPENAI_MODEL", "gpt-4o-mini"),

        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=_getenv("GEMINI_MODEL", "gemini-2.0-flash"),

        project_repo_mode=_getenv("PROJECT_REPO_MODE", "memory").lower(),
        project_repo_path=_getenv("PROJECT_REPO_PATH", "data/projects.json"),
        upload_dir=_getenv("UPLOAD_DIR", "uploads"),
    )

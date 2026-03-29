"""Application configuration."""
from pathlib import Path

try:
    from pydantic_settings import BaseSettings
except ImportError:
    BaseSettings = None  # type: ignore

_BASE = Path(__file__).resolve().parents[2]


def _default_paths():
    return {
        "data_dir": _BASE / "data",
        "upload_dir": _BASE / "uploads",
        "chroma_persist_dir": _BASE / "chroma_db",
    }


if BaseSettings is not None:

    class Settings(BaseSettings):
        app_name: str = "Med Insight AI"
        debug: bool = False
        data_dir: Path = _default_paths()["data_dir"]
        upload_dir: Path = _default_paths()["upload_dir"]
        chroma_persist_dir: Path = _default_paths()["chroma_persist_dir"]
        cors_origins: list = ["http://localhost:5173", "http://127.0.0.1:5173"]
        chunk_size: int = 500
        chunk_overlap: int = 100
        medical_collection_name: str = "medical_dictionary"
        documents_collection_name: str = "user_documents"
        tesseract_lang: str = "eng"

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
else:
    # Fallback when pydantic_settings is not installed
    class Settings:
        app_name: str = "Med Insight AI"
        debug: bool = False
        data_dir: Path = _default_paths()["data_dir"]
        upload_dir: Path = _default_paths()["upload_dir"]
        chroma_persist_dir: Path = _default_paths()["chroma_persist_dir"]
        cors_origins: list = ["http://localhost:5173", "http://127.0.0.1:5173"]
        chunk_size: int = 500
        chunk_overlap: int = 100
        medical_collection_name: str = "medical_dictionary"
        documents_collection_name: str = "user_documents"
        tesseract_lang: str = "eng"


def get_settings() -> Settings:
    return Settings()


settings = get_settings()

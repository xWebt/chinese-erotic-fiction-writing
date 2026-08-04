"""Configuration management for the fiction harness.

Reads from ~/.fiction-harness/config.yaml and env vars.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import yaml


CONFIG_DIR = Path.home() / ".fiction-harness"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


@dataclass
class Config:
    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Corpus paths
    corpus_dir: str = ""
    anchor_works: list[str] = field(default_factory=list)

    # Index
    index_dir: str = ""
    # Technique fingerprint output (shareable, no copyright issues)
    fingerprints_dir: str = ""

    # Generation defaults
    default_word_count: int = 5000
    max_continue_rounds: int = 4  # max auto-continue rounds per chapter

    # Quality thresholds
    min_passage_length: int = 100
    max_encoding_error_rate: float = 0.05
    min_dedup_similarity: float = 0.8

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        path = path or CONFIG_FILE
        cfg = cls()
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        # Env overrides
        if os.environ.get("DEEPSEEK_API_KEY"):
            cfg.deepseek_api_key = os.environ["DEEPSEEK_API_KEY"]
        if os.environ.get("DEEPSEEK_BASE_URL"):
            cfg.deepseek_base_url = os.environ["DEEPSEEK_BASE_URL"]
        if not cfg.index_dir:
            cfg.index_dir = str(CONFIG_DIR / "index")
        if not cfg.fingerprints_dir:
            cfg.fingerprints_dir = str(CONFIG_DIR / "fingerprints")
        return cfg

    def save(self, path: Optional[Path] = None):
        path = path or CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        with open(path, "w") as f:
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)

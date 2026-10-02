"""Runtime configuration. Environment variables and an optional .env file, no extra dependency."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _truthy(v) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def _path(v: str, base: Path) -> Path:
    p = Path(v).expanduser()
    return p if p.is_absolute() else (base / p)


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    input_dir: Path = ROOT / "data" / "input"
    artifact_dir: Path = ROOT / "artifacts"
    plugins_dir: Path = ROOT / "plugins"
    skills_dir: Path = ROOT / "skills"
    output_dir: Path = ROOT / "output"
    templates_dir: Path = ROOT / "docs" / "templates"
    schema_file: Path = ROOT / "config" / "datasets.json"
    rules_file: Path = ROOT / "rules.json"
    excel_sheet: str = ""
    watch_interval: float = 5.0
    auto_train: bool = False
    fast: bool = False
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls, root: Path = ROOT, environ: dict | None = None) -> "Settings":
        env = {**_load_dotenv(root / ".env"), **(environ if environ is not None else os.environ)}
        g = lambda k, d="": env.get(k, d)
        return cls(
            root=root,
            input_dir=_path(g("KESTREL_INPUT_DIR", "data/input"), root),
            artifact_dir=_path(g("KESTREL_ARTIFACT_DIR", "artifacts"), root),
            plugins_dir=_path(g("KESTREL_PLUGINS_DIR", "plugins"), root),
            skills_dir=_path(g("KESTREL_SKILLS_DIR", "skills"), root),
            output_dir=_path(g("KESTREL_OUTPUT_DIR", "output"), root),
            templates_dir=_path(g("KESTREL_TEMPLATES_DIR", "docs/templates"), root),
            schema_file=_path(g("KESTREL_SCHEMA_FILE", "config/datasets.json"), root),
            rules_file=_path(g("KESTREL_RULES_FILE", "rules.json"), root),
            excel_sheet=g("KESTREL_EXCEL_SHEET", ""),
            watch_interval=float(g("KESTREL_WATCH_INTERVAL", "5") or 0),
            auto_train=_truthy(g("KESTREL_AUTO_TRAIN", "false")),
            fast=_truthy(g("KESTREL_FAST", "false")),
            log_level=g("KESTREL_LOG_LEVEL", "INFO").upper(),
            host=g("KESTREL_HOST", "127.0.0.1"),
            port=int(g("KESTREL_PORT", "8000")),
        )

    def ensure_dirs(self) -> None:
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    @property
    def model_path(self) -> Path:
        return self.artifact_dir / "model.joblib"

    @property
    def metrics_path(self) -> Path:
        return self.artifact_dir / "metrics.json"

    @property
    def state_path(self) -> Path:
        return self.artifact_dir / "state.json"

    @property
    def predictions_path(self) -> Path:
        return self.artifact_dir / "predictions.csv"

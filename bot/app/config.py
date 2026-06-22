from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _parse_optional_channel_id(raw: str | None) -> int | None:
    if not raw:
        return None
    text = raw.strip()
    if not text or text in ("0", "-", "none"):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_admin_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return ids


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: list[int] = field(default_factory=list)
    db_path: Path = Path("netfly.db")
    required_channel_id: int | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token) and self.bot_token != "123456:ABC-DEF_your_token_here"


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    admins = _parse_admin_ids(os.getenv("ADMIN_IDS"))
    db_path = Path(os.getenv("DB_PATH", "netfly.db"))
    req_ch = _parse_optional_channel_id(os.getenv("REQUIRED_CHANNEL_ID"))
    return Settings(
        bot_token=token,
        admin_ids=admins,
        db_path=db_path,
        required_channel_id=req_ch,
    )

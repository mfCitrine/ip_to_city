"""DB-IP 下载器。

DB-IP Lite 免费版，CC BY 4.0，需回链署名。
城市级：dbip-city-lite。
"""

from __future__ import annotations

from pathlib import Path

from .common import download

# DB-IP Lite 月度免费包（mmdb 格式）
DBIP_CITY_MMDB = "https://download.db-ip.com/free/dbip-city-lite-2026-01.mmdb.gz"


def download_dbip(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "dbip-city-lite.mmdb.gz"
    return download(DBIP_CITY_MMDB, dest)

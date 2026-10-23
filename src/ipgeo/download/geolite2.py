"""GeoLite2 下载器。

需要 MaxMind 账号与 License Key（免费注册）。
数据：GeoLite2-City / GeoLite2-ASN（mmdb 格式），CC BY-SA 4.0 + EULA。

注意：MaxMind 从 2024 年起因美国「批量敏感数据出境」法规，
禁止从中国大陆（CN）下载，会返回 HTTP 451。因此本下载器需在
海外环境（如 GitHub Actions runner）运行。
"""

from __future__ import annotations

import os
from pathlib import Path

import requests

DOWNLOAD_BASE = "https://download.maxmind.com/geoip/databases"


def _download_edition(edition: str, out_dir: Path, account_id: str,
                      license_key: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    url = f"{DOWNLOAD_BASE}/{edition}/download"
    dest = out_dir / f"{edition}.tar.gz"
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    r = requests.get(url, auth=(account_id, license_key),
                     params={"suffix": "tar.gz"}, timeout=180, stream=True)
    if r.status_code == 451:
        raise RuntimeError(
            "GeoLite2 禁止从中国大陆下载（HTTP 451，美国数据出境法规）。"
            "请在海外环境（如 GitHub Actions）运行，或改用 DB-IP/纯真。"
        )
    r.raise_for_status()
    tmp = dest.with_suffix(".tar.gz.part")
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 256):
            f.write(chunk)
    os.replace(tmp, dest)
    return dest


def download_geolite2(out_dir: Path) -> dict[str, Path]:
    account_id = os.environ.get("MAXMIND_ACCOUNT_ID", "")
    license_key = os.environ.get("MAXMIND_LICENSE_KEY", "")
    if not account_id or not license_key:
        raise RuntimeError(
            "缺少 MaxMind 凭证：请设置环境变量 MAXMIND_ACCOUNT_ID 与 "
            "MAXMIND_LICENSE_KEY（或写入 scripts/.env 后 source）"
        )
    results: dict[str, Path] = {}
    for edition in ("GeoLite2-City", "GeoLite2-ASN"):
        results[edition] = _download_edition(
            edition, out_dir, account_id, license_key
        )
    return results

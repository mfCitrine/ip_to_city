"""GeoLite2 下载器。

需要 MaxMind 账号与 License Key（免费注册）。
数据：GeoLite2-City / GeoLite2-ASN（mmdb 格式），CC BY-SA 4.0 + EULA。
"""

from __future__ import annotations

import os
from pathlib import Path

from .common import download

GEOIP_URL = "https://download.maxmind.com/app/geoip_download"


def download_geolite2(out_dir: Path) -> dict[str, Path]:
    account_id = os.environ.get("MAXMIND_ACCOUNT_ID", "")
    license_key = os.environ.get("MAXMIND_LICENSE_KEY", "")
    if not account_id or not license_key:
        raise RuntimeError(
            "缺少 MaxMind 凭证：请设置环境变量 MAXMIND_ACCOUNT_ID 与 "
            "MAXMIND_LICENSE_KEY（或写入 scripts/.env 后 source）"
        )
    auth = (account_id, license_key)
    files = {
        "city": f"{GEOIP_URL}?edition_id=GeoLite2-City&license_key={license_key}&suffix=tar.gz",
        "asn": f"{GEOIP_URL}?edition_id=GeoLite2-ASN&license_key={license_key}&suffix=tar.gz",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}
    for name, url in files.items():
        dest = out_dir / f"GeoLite2-{name.capitalize()}.tar.gz"
        download(url, dest, headers={"User-Agent": "ipgeo/0.1"})
        results[name] = dest
    return results

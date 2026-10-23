"""DB-IP 下载器。

DB-IP Lite 免费版，CC BY 4.0，需回链署名（https://db-ip.com）。
城市级：dbip-city-lite；ASN：dbip-asn-lite。
月度更新，文件名含年月，如 dbip-city-lite-2026-10.mmdb.gz。

从中国境内可直接下载（已验证）。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .common import download

# DB-IP Lite 月度免费包（mmdb.gz 格式），URL 中的年月按月滚动
_BASE = "https://download.db-ip.com/free"


def _month_tag() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def download_dbip_city(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    url = f"{_BASE}/dbip-city-lite-{_month_tag()}.mmdb.gz"
    return download(url, out_dir / "dbip-city-lite.mmdb.gz")


def download_dbip_city_csv(out_dir: Path) -> Path:
    """下载 DB-IP city-lite 的 CSV 格式（高性能整数区间解析用）。

    CSV 格式同样公开可下载（已验证），文件名含年月，如
    dbip-city-lite-2026-10.csv.gz。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    url = f"{_BASE}/dbip-city-lite-{_month_tag()}.csv.gz"
    return download(url, out_dir / "dbip-city-lite.csv.gz")


def download_dbip_asn(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    url = f"{_BASE}/dbip-asn-lite-{_month_tag()}.mmdb.gz"
    return download(url, out_dir / "dbip-asn-lite.mmdb.gz")


def download_dbip(out_dir: Path) -> dict[str, Path]:
    """下载 city + asn，返回 {name: path}。"""
    results: dict[str, Path] = {}
    try:
        results["city"] = download_dbip_city(out_dir)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] DB-IP City 下载失败（跳过）: {e}")
    try:
        results["asn"] = download_dbip_asn(out_dir)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] DB-IP ASN 下载失败（跳过）: {e}")
    return results

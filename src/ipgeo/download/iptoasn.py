"""iptoasn.com IP→ASN 下载器。

数据：ip2asn-combined.tsv.gz（tsv：range_start, range_end, ASN, country, description）。
用途：国家归属仲裁的权威源（origin AS 的国家）。
License：免费（需署名 iptoasn.com）。
国内访问需代理（已通过 GitHub Actions / 本地代理下载）。
"""

from __future__ import annotations

from pathlib import Path

from .common import download

IPTOASN_URL = "https://iptoasn.com/data/ip2asn-combined.tsv.gz"


def download_iptoasn(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return download(IPTOASN_URL, out_dir / "ip2asn.tsv.gz")

"""RIR 分配数据下载器（国家维度权威基准）。

数据来自 5 大 RIR 的已分配地址段统计文件（delegated-*）：
- APNIC: https://ftp.apnic.net/stats/apnic/delegated-apnic-latest
- ARIN: https://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest
- RIPE: https://ftp.ripe.net/ripe/stats/delegated-ripencc-latest
- LACNIC: https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest
- AFRINIC: https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest

文件格式（每行以 | 分隔）：
  registry|cc|type|start|value|date|status[|extensions]
  type 为 ipv4 时，start 是起始地址，value 是地址数量。
"""

from __future__ import annotations

from pathlib import Path

from .common import download

RIR_SOURCES = {
    "apnic": "https://ftp.apnic.net/stats/apnic/delegated-apnic-latest",
    "arin": "https://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest",
    "ripencc": "https://ftp.ripe.net/ripe/stats/delegated-ripencc-latest",
    "lacnic": "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest",
    "afrinic": "https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest",
}


def download_rir(out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}
    for name, url in RIR_SOURCES.items():
        dest = out_dir / f"delegated-{name}-latest"
        try:
            download(url, dest)
            results[name] = dest
        except Exception as e:  # noqa: BLE001
            print(f"[warn] RIR {name} 下载失败（跳过）: {e}")
    return results

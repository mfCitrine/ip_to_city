"""人工订正数据加载：corrections.csv → 最高优先级 MergedRecord。

格式：network,country,province,city,isp,source,evidence,date
订正记录在构建流程中最后写入 mmdb（利用 mmdb_writer 后写覆盖特性），
因此优先级最高，覆盖一切自动融合结果。
"""

from __future__ import annotations

import csv
from pathlib import Path

from .vote import MergedRecord


def load_corrections(csv_path: Path) -> list[MergedRecord]:
    if not csv_path.exists():
        return []
    records: list[MergedRecord] = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        # 跳过注释行（# 开头），并去除表头可能的 BOM
        lines = [ln for ln in f if not ln.lstrip().startswith("#")]
    reader = csv.DictReader(lines)
    for row in reader:
        network = (row.get("network") or "").strip()
        if not network:
            continue
        records.append(MergedRecord(
            network=network,
            country=(row.get("country") or "").strip(),
            province=(row.get("province") or "").strip(),
            city=(row.get("city") or "").strip(),
            isp=(row.get("isp") or "").strip(),
            asn="",
            network_type="isp",
            confidence=100,  # 人工订正，置信度最高
            sources=["manual"],
        ))
    return records

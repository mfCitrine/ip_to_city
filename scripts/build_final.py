"""最终构建：分层融合（中国区用纯真，非中国区用 DB-IP）。

策略（MVP）：
  1. DB-IP 解析全量，按 country 拆中国段与非中国段。
  2. 中国区：用纯真数据（国内省市区精度最高，覆盖 DB-IP 中国段）。
  3. 非中国区：用 DB-IP（全球城市级）。
  4. 合并输出 mmdb + csv。

说明：纯真与 DB-IP 在国家归属上的边界冲突（如 101.47.x 部分段），
以 DB-IP 的 country 字段为准进行大分类；这类「中外出让边界」IP 的
精确归属留待 Phase 2 用 BGP/ASN 与人工订正解决。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ipgeo.merge.dbip_grouped import parse_dbip_csv_v4  # noqa: E402
from ipgeo.merge.cz88_export import export_cn_records  # noqa: E402
from ipgeo.merge.vote import MergedRecord, Record  # noqa: E402
from ipgeo.output.writer import write_mmdb, write_csv  # noqa: E402

DATA_RAW = ROOT / "data" / "raw"
DATA_RELEASE = ROOT / "data" / "release"


def _rec_to_merged(r: Record, confidence: int) -> MergedRecord:
    return MergedRecord(
        network=r.network, country=r.country, province=r.province,
        city=r.city, isp=r.isp, asn=r.asn,
        network_type="isp", confidence=confidence, sources=[r.source],
    )


def main():
    t0 = time.time()

    print("[1/5] 解析 DB-IP ...")
    dbip = parse_dbip_csv_v4(DATA_RAW / "dbip" / "dbip-city-lite.csv.gz")
    dbip_other = [r for r in dbip if r.country != "CN"]
    print(f"  DB-IP 非中国 {len(dbip_other)} 段")

    print("[2/5] 导出纯真中国区 ...")
    cz88_path = DATA_RAW / "cz88" / "qqwry.dat"
    if cz88_path.exists():
        cz88 = export_cn_records(cz88_path)
        print(f"  纯真中国区 {len(cz88)} 段")
    else:
        cz88 = []
        print("  [warn] 纯真缺失")

    print("[3/5] 分层融合 ...")
    if cz88:
        merged_records = [_rec_to_merged(r, confidence=80) for r in cz88]
    else:
        dbip_cn = [r for r in dbip if r.country == "CN"]
        merged_records = [_rec_to_merged(r, confidence=60) for r in dbip_cn]
    merged_records += [_rec_to_merged(r, confidence=60) for r in dbip_other]
    print(f"  合计 {len(merged_records)} 段")

    print("[4/5] 输出 mmdb ...")
    t1 = time.time()
    write_mmdb(merged_records, DATA_RELEASE / "ipgeo-city.mmdb")
    print(f"  mmdb 完成 {round(time.time() - t1, 1)}s")

    print("[5/5] 输出 csv ...")
    write_csv(merged_records, DATA_RELEASE / "ipgeo-city.csv")

    print(f"\n总耗时 {round(time.time() - t0, 1)}s")
    print(f"输出: {DATA_RELEASE / 'ipgeo-city.mmdb'}")
    print(f"输出: {DATA_RELEASE / 'ipgeo-city.csv'}")


if __name__ == "__main__":
    main()

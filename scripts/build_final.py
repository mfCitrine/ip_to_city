"""Phase 2 构建：人工订正 + ASN 国家仲裁 + ASN 增强 的分层融合。

流程：
  1. 解析 DB-IP（全量），构建 IP→country 范围索引。
  2. 导出纯真中国区段。
  3. 加载 iptoasn（origin AS 国家，权威仲裁源）。
  4. 纯真段仲裁：
     - DB-IP 也判中国 → 无冲突，保留（避开 anycast 误导）。
     - DB-IP 判国外 → 冲突，查 iptoasn：iptoasn 判中国则保留纯真，
       否则视为「假中国段」剔除（该 IP 实际已转让国外，交给 DB-IP 覆盖）。
     同时用 iptoasn 的 ASN/描述增强国内段的运营商字段。
  5. 合并：纯真真中国段 + DB-IP 非中国段 + 人工订正（最高优先级，最后写入）。
  6. 输出 mmdb + csv。
"""

from __future__ import annotations

import ipaddress
import socket
import struct
import sys
import time
from array import array
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ipgeo.merge.dbip_grouped import parse_dbip_csv_v4  # noqa: E402
from ipgeo.merge.cz88_export import export_cn_records  # noqa: E402
from ipgeo.merge.iptoasn import IptoasnIndex  # noqa: E402
from ipgeo.merge.corrections import load_corrections  # noqa: E402
from ipgeo.merge.vote import MergedRecord, Record  # noqa: E402
from ipgeo.output.writer import write_mmdb, write_csv  # noqa: E402

DATA_RAW = ROOT / "data" / "raw"
DATA_RELEASE = ROOT / "data" / "release"
CORRECTIONS = ROOT / "corrections.csv"

# 字符串驻留缓存：城市/省份/ISP 等字段在数百万记录间大量重复，
# 去重后可节省数 GB 内存（OOM 关键优化）
_str_cache: dict[str, str] = {}


def _intern(s: str) -> str:
    return _str_cache.setdefault(s, s)


def _ip2int(ip: str) -> int:
    return struct.unpack("!I", socket.inet_aton(ip))[0]


def _rec_to_merged(r: Record, confidence: int) -> MergedRecord:
    return MergedRecord(
        network=r.network, country=_intern(r.country),
        province=_intern(r.province), city=_intern(r.city),
        isp=_intern(r.isp), asn=_intern(r.asn),
        network_type="isp", confidence=confidence, sources=[r.source],
    )


def main():
    t0 = time.time()

    print("[1/6] 解析 DB-IP ...")
    dbip = parse_dbip_csv_v4(DATA_RAW / "dbip" / "dbip-city-lite.csv.gz")
    dbip_other = [r for r in dbip if r.country != "CN"]
    dbip_cn = [r for r in dbip if r.country == "CN"]
    print(f"  DB-IP 非中国 {len(dbip_other)} 段，中国 {len(dbip_cn)} 段")

    # 构建 DB-IP country 范围索引（平行数组，比元组列表省 ~700MB）
    print("  构建 DB-IP country 索引 ...")
    range_starts = array("I")
    range_ends = array("I")
    range_countries: list[str] = []
    for r in dbip:
        cidr = r.network
        base = cidr.split("/")[0]
        s = _ip2int(base)
        plen = int(cidr.split("/")[1])
        e = s + (1 << (32 - plen)) - 1
        range_starts.append(s)
        range_ends.append(e)
        range_countries.append(_intern(r.country))
    order = sorted(range(len(range_starts)), key=lambda i: range_starts[i])
    range_starts = array("I", (range_starts[i] for i in order))
    range_ends = array("I", (range_ends[i] for i in order))
    range_countries = [range_countries[i] for i in order]
    del dbip, order  # 释放 780 万 Record 对象容器
    print(f"  DB-IP 索引 {len(range_starts)} 段")

    # 提前把 DB-IP 记录转成 MergedRecord，释放数百万原始 Record
    dbip_other_m = [_rec_to_merged(r, confidence=60) for r in dbip_other]
    del dbip_other
    dbip_cn_m = [_rec_to_merged(r, confidence=60) for r in dbip_cn]
    del dbip_cn

    print("[2/6] 导出纯真中国区 ...")
    cz88_path = DATA_RAW / "cz88" / "qqwry.dat"
    cz88 = export_cn_records(cz88_path) if cz88_path.exists() else []
    print(f"  纯真中国区 {len(cz88)} 段")

    # 若纯真缺失（如 GitHub Actions 无私有数据），中国区由 DB-IP 中国段兜底
    if not cz88:
        print("  [warn] 纯真缺失，中国区降级为 DB-IP 中国段兜底（省市区精度降低）")

    print("[3/6] 加载 iptoasn 索引 ...")
    ip2asn_path = DATA_RAW / "ip2asn.tsv.gz"
    iptoasn = IptoasnIndex(ip2asn_path) if ip2asn_path.exists() else None
    print(f"  iptoasn {len(iptoasn) if iptoasn else 0} 段")

    print("[4/6] 纯真段国家仲裁 ...")
    keep_cn: list[Record] = []
    removed: list[Record] = []
    for r in cz88:
        start_ip = r.network.split("/")[0]
        start_int = _ip2int(start_ip)
        idx = bisect_right(range_starts, start_int) - 1
        dbip_country = ""
        if idx >= 0 and start_int <= range_ends[idx]:
            dbip_country = range_countries[idx]

        if dbip_country == "CN" or dbip_country == "":
            # 无冲突（DB-IP 也判中国，或 DB-IP 未覆盖）→ 保留纯真
            keep_cn.append(r)
        else:
            # 冲突：纯真说中国、DB-IP 说国外，用 iptoasn 仲裁
            asn_info = iptoasn.lookup(start_ip) if iptoasn else None
            if asn_info and asn_info[0] == "CN":
                # iptoasn origin AS 也是中国 → 纯真对，保留并增强 ASN
                r.asn = str(asn_info[1])
                keep_cn.append(r)
            else:
                # 实际已转让国外 → 假中国段，剔除
                removed.append(r)

    print(f"  保留中国段 {len(keep_cn)}，剔除假中国段 {len(removed)}")
    del removed

    # 纯真缺失时，用 DB-IP 中国段兜底（并做 ASN 增强）
    if not cz88:
        if iptoasn:
            enhanced = 0
            for r in dbip_cn_m:
                if not r.asn:
                    info = iptoasn.lookup(r.network.split("/")[0])
                    if info and info[0] == "CN":
                        r.asn = str(info[1])
                        enhanced += 1
            print(f"  DB-IP 中国兜底段 ASN 增强 {enhanced} 段")

    # ASN 增强：对保留的国内段，用 iptoasn 补 ASN 与英文运营商名
    if cz88 and iptoasn:
        enhanced = 0
        for r in keep_cn:
            if not r.asn:
                info = iptoasn.lookup(r.network.split("/")[0])
                if info and info[0] == "CN":
                    r.asn = str(info[1])
                    enhanced += 1
        print(f"  国内段 ASN 增强 {enhanced} 段")

    print("[5/6] 合并输出 ...")
    merged = [_rec_to_merged(r, confidence=80) for r in keep_cn]
    del keep_cn, cz88
    merged += dbip_other_m
    del dbip_other_m, dbip_cn_m
    # 人工订正最高优先级，最后写入（mmdb 后写覆盖）
    corrections = load_corrections(CORRECTIONS)
    merged += corrections
    print(f"  合并总计 {len(merged)} 段（含订正 {len(corrections)} 段）")

    t1 = time.time()
    write_mmdb(merged, DATA_RELEASE / "ipgeo-city.mmdb")
    print(f"  mmdb 完成 {round(time.time() - t1, 1)}s")

    write_csv(merged, DATA_RELEASE / "ipgeo-city.csv")

    print(f"\n总耗时 {round(time.time() - t0, 1)}s")
    print(f"输出: {DATA_RELEASE / 'ipgeo-city.mmdb'}")
    print(f"输出: {DATA_RELEASE / 'ipgeo-city.csv'}")


if __name__ == "__main__":
    main()

"""端到端演示：用真实 RIR(APNIC) 数据 + 演示城市数据，产出可查询的首版 mmdb。

用途：在没有 GeoLite2/DB-IP 凭证时，也能验证完整 Pipeline 并产出一个
可用的演示库。配置好凭证后改用 scripts/run_pipeline.py 产出正式库。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ipgeo.download import rir as rir_dl            # noqa: E402
from ipgeo.merge import parsers                     # noqa: E402
from ipgeo.merge.aggregate import aggregate, resolve_overlap  # noqa: E402
from ipgeo.merge.vote import Record                 # noqa: E402
from ipgeo.output.writer import write_mmdb, write_csv  # noqa: E402

DATA_RAW = ROOT / "data" / "raw"
DATA_RELEASE = ROOT / "data" / "release"

# 演示用的已知 IP 段（多源一致，用于展示融合效果）
DEMO_RECORDS = [
    # 114.114.114.114 = 南京电信 DNS
    Record("114.114.114.0/24", "rir", country="CN"),
    Record("114.114.114.0/24", "geolite2", country="CN", province="江苏省", city="南京市", isp="中国电信"),
    Record("114.114.114.0/24", "dbip", country="CN", province="江苏省", city="南京市"),
    # 8.8.8.8 = Google DNS（美国）
    Record("8.8.8.0/24", "rir", country="US"),
    Record("8.8.8.0/24", "geolite2", country="US", province="California", city="Mountain View", isp="Google"),
    Record("8.8.8.0/24", "dbip", country="US", province="California", city="Mountain View"),
    # 223.5.5.5 = 阿里 DNS（杭州）
    Record("223.5.5.0/24", "rir", country="CN"),
    Record("223.5.5.0/24", "geolite2", country="CN", province="浙江省", city="杭州市", isp="阿里云"),
    Record("223.5.5.0/24", "dbip", country="CN", province="浙江省", city="杭州市"),
    # 1.1.1.1 = Cloudflare（澳大利亚示例，演示冲突）
    Record("1.1.1.0/24", "rir", country="AU"),
    Record("1.1.1.0/24", "geolite2", country="AU", city="Sydney"),
    Record("1.1.1.0/24", "dbip", country="US", city="Los Angeles"),
]


def main():
    print("== ipgeo 端到端演示 ==")
    records: list[Record] = list(DEMO_RECORDS)

    # 1. 尝试加载真实 APNIC 数据（国家维度）
    apnic = DATA_RAW / "rir" / "delegated-apnic-latest"
    if not apnic.exists():
        print("[1/4] 下载 APNIC 数据 ...")
        try:
            rir_dl.download_rir(DATA_RAW / "rir")
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] RIR 下载部分失败（继续用演示数据）: {e}")
    if apnic.exists():
        apnic_records = parsers.parse_rir_delegated(apnic)
        print(f"[2/4] 解析 APNIC：{len(apnic_records)} 个网段（国家维度）")
        records.extend(apnic_records)
    else:
        print("[2/4] 未找到 APNIC 数据，仅用演示数据")

    # 2. 融合
    print(f"[3/4] 融合 {len(records)} 条记录 ...")
    merged = aggregate(records)
    merged = resolve_overlap(merged)
    print(f"  得到 {len(merged)} 个网段")

    # 3. 输出
    print("[4/4] 输出 ...")
    DATA_RELEASE.mkdir(parents=True, exist_ok=True)
    mmdb_path = write_mmdb(merged, DATA_RELEASE / "ipgeo-city.mmdb")
    csv_path = write_csv(merged, DATA_RELEASE / "ipgeo-city.csv")
    print(f"  完成: {mmdb_path}")
    print(f"  完成: {csv_path}")

    # 4. 验证查询
    print("\n== 验证查询 ==")
    import maxminddb
    with maxminddb.open_database(str(mmdb_path)) as reader:
        for ip in ("114.114.114.114", "8.8.8.8", "223.5.5.5", "1.1.1.1"):
            d = reader.get(ip)
            if d:
                cn = d["country"]["iso_code"]
                city = (d.get("city") or {}).get("names", {}).get("zh-CN", "")
                conf = d.get("traits", {}).get("confidence", "")
                isp = d.get("traits", {}).get("isp", "")
                print(f"  {ip:16s} -> {cn:3s} {city:8s} conf={conf} isp={isp}")
    print("\n演示完成 ✓")


if __name__ == "__main__":
    main()

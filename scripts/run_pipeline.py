"""主 Pipeline：下载 → 解析 → 融合 → 输出。

用法：
  python scripts/run_pipeline.py                 # 全流程
  python scripts/run_pipeline.py --download-only # 仅下载
  python scripts/run_pipeline.py --build-only    # 仅构建（使用已下载数据）
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 允许直接运行 scripts/ 下的脚本时导入 src
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ipgeo.download import rir as rir_dl            # noqa: E402
from ipgeo.download import dbip as dbip_dl          # noqa: E402
from ipgeo.download import geolite2 as gl2_dl       # noqa: E402
from ipgeo.merge import parsers                     # noqa: E402
from ipgeo.merge.aggregate import aggregate, resolve_overlap  # noqa: E402
from ipgeo.output.writer import write_mmdb, write_csv  # noqa: E402

DATA_RAW = ROOT / "data" / "raw"
DATA_BUILD = ROOT / "data" / "build"
DATA_RELEASE = ROOT / "data" / "release"


def load_env():
    """加载 scripts/.env（若存在）。"""
    env_file = ROOT / "scripts" / ".env"
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def do_download():
    print("[1/4] 下载数据源 ...")
    # RIR（国家权威，无需凭证）
    rir_dl.download_rir(DATA_RAW / "rir")
    # DB-IP（免费，需回链署名）
    try:
        dbip_dl.download_dbip(DATA_RAW / "dbip")
    except Exception as e:  # noqa: BLE001
        print(f"[warn] DB-IP 下载失败（跳过）: {e}")
    # GeoLite2（需 MaxMind 凭证）
    try:
        gl2_dl.download_geolite2(DATA_RAW / "geolite2")
    except Exception as e:  # noqa: BLE001
        print(f"[warn] GeoLite2 下载失败（跳过）: {e}")
    print("下载完成。")


def do_build():
    print("[2/4] 解析数据源 ...")
    records: list[Record] = []

    # RIR
    rir_dir = DATA_RAW / "rir"
    if rir_dir.exists():
        for f in rir_dir.glob("delegated-*"):
            records.extend(parsers.parse_rir_delegated(f))
            print(f"  RIR {f.name}: 已解析")
    else:
        print("  [warn] RIR 数据缺失")

    # GeoLite2
    gl2_dir = DATA_RAW / "geolite2"
    if gl2_dir.exists():
        tar_files = list(gl2_dir.glob("*.tar.gz"))
        if tar_files:
            extract = DATA_BUILD / "geolite2"
            for tf in tar_files:
                parsers.extract_tarball(tf, extract)
            city_mmdb = _find(extract, "City.mmdb")
            asn_mmdb = _find(extract, "ASN.mmdb")
            if city_mmdb:
                records.extend(parsers.parse_geolite2_city(city_mmdb))
                print("  GeoLite2-City: 已解析")
            if asn_mmdb:
                records.extend(parsers.parse_geolite2_asn(asn_mmdb))
                print("  GeoLite2-ASN: 已解析")
        else:
            print("  [warn] GeoLite2 tar.gz 缺失")
    else:
        print("  [warn] GeoLite2 目录缺失")

    # DB-IP
    dbip_dir = DATA_RAW / "dbip"
    if dbip_dir.exists():
        gz_files = list(dbip_dir.glob("*.mmdb.gz"))
        if gz_files:
            mmdb_path = parsers.gunzip(gz_files[0], DATA_BUILD / "dbip" / "dbip-city.mmdb")
            records.extend(parsers.parse_dbip_city(mmdb_path))
            print("  DB-IP: 已解析")
        else:
            print("  [warn] DB-IP 数据缺失")

    if not records:
        print("✗ 无任何数据源可用，无法构建。请先运行 --download-only 并配置凭证。")
        sys.exit(1)

    print(f"[3/4] 融合 {len(records)} 条记录 ...")
    merged = aggregate(records)
    merged = resolve_overlap(merged)
    print(f"  融合得到 {len(merged)} 个网段")

    print("[4/4] 输出结果 ...")
    DATA_RELEASE.mkdir(parents=True, exist_ok=True)
    write_mmdb(merged, DATA_RELEASE / "ipgeo-city.mmdb")
    write_csv(merged, DATA_RELEASE / "ipgeo-city.csv")
    print("完成！输出文件：")
    print(f"  - {DATA_RELEASE / 'ipgeo-city.mmdb'}")
    print(f"  - {DATA_RELEASE / 'ipgeo-city.csv'}")


def _find(root: Path, keyword: str) -> Path | None:
    for p in root.rglob("*.mmdb"):
        if keyword in p.name:
            return p
    return None


def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--download-only", action="store_true")
    ap.add_argument("--build-only", action="store_true")
    args = ap.parse_args()

    if args.download_only:
        do_download()
    elif args.build_only:
        do_build()
    else:
        do_download()
        do_build()


if __name__ == "__main__":
    main()

"""Phase 2 数据源下载脚本（供 GitHub Actions 使用）。

下载 build_final.py 所需的数据源：
  - DB-IP city-lite CSV（公开，国内/海外均可下）
  - iptoasn ip2asn-combined.tsv.gz（公开，海外可下；国内需代理）
  - 纯真 qqwry.dat（可选，通过环境变量 CZ88_URL 指向私有 URL 拉取）

用法：
  python scripts/download_phase2.py            # 下载 DB-IP + iptoasn
  python scripts/download_phase2.py --with-cz88 # 额外尝试拉取纯真（需 CZ88_URL）
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ipgeo.download import dbip as dbip_dl       # noqa: E402
from ipgeo.download import iptoasn as iptoasn_dl # noqa: E402
from ipgeo.download.common import download       # noqa: E402

DATA_RAW = ROOT / "data" / "raw"


def download_cz88_from_url():
    """从环境变量 CZ88_URL 拉取纯真 qqwry.dat（可选私有数据源）。

    纯真 License 不允许把 qqwry.dat 提交进公开仓库再分发，因此这里通过
    私有 URL（用户自行托管在私有对象存储/私有 gist 等）拉取，URL 通过
    GitHub Actions Secret 传入，不进仓库文件。
    """
    url = os.environ.get("CZ88_URL", "").strip()
    if not url:
        print("[info] 未配置 CZ88_URL，跳过纯真下载（中国区将用 DB-IP 兜底）")
        return
    out = DATA_RAW / "cz88"
    out.mkdir(parents=True, exist_ok=True)
    try:
        download(url, out / "qqwry.dat")
        print(f"[ok] 纯真 qqwry.dat 已下载：{out / 'qqwry.dat'}")
    except Exception as e:  # noqa: BLE001
        print(f"[warn] 纯真下载失败（跳过，中国区用 DB-IP 兜底）: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-cz88", action="store_true",
                    help="尝试从 CZ88_URL 拉取纯真数据")
    args = ap.parse_args()

    print("[1/3] 下载 DB-IP city-lite CSV ...")
    try:
        dbip_dl.download_dbip_city_csv(DATA_RAW / "dbip")
    except Exception as e:  # noqa: BLE001
        print(f"[warn] DB-IP CSV 下载失败: {e}")

    print("[2/3] 下载 iptoasn ...")
    try:
        iptoasn_dl.download_iptoasn(DATA_RAW)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] iptoasn 下载失败: {e}")

    if args.with_cz88:
        print("[3/3] 尝试下载纯真（可选）...")
        download_cz88_from_url()
    else:
        print("[3/3] 跳过纯真（未指定 --with-cz88）")

    print("下载完成。")


if __name__ == "__main__":
    main()

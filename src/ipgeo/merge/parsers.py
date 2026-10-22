"""各数据源解析器：将原始数据转换为统一的 Record 列表。

统一使用 maxminddb 读取 mmdb 数据；RIR 文本自行解析。
"""

from __future__ import annotations

import gzip
import ipaddress
import shutil
import tarfile
from pathlib import Path

from ..utils.iputil import normalize_city, normalize_country, normalize_province
from .vote import Record


def parse_geolite2_city(mmdb_path: Path) -> list[Record]:
    """解析 GeoLite2-City.mmdb。"""
    import maxminddb
    records: list[Record] = []
    with maxminddb.open_database(str(mmdb_path)) as reader:
        for net, data in reader:
            country = (data.get("country") or {}).get("iso_code", "")
            subs = data.get("subdivisions") or [{}]
            province = (subs[0].get("names") or {}).get("zh-CN", "") if subs else ""
            city = ((data.get("city") or {}).get("names") or {}).get("zh-CN", "")
            if not province:
                province = (subs[0].get("names") or {}).get("en", "") if subs else ""
            records.append(Record(
                network=str(net),
                source="geolite2",
                country=country,
                province=normalize_province(province),
                city=normalize_city(city),
            ))
    return records


def parse_geolite2_asn(mmdb_path: Path) -> list[Record]:
    """解析 GeoLite2-ASN.mmdb，提取 ASN。"""
    import maxminddb
    records: list[Record] = []
    with maxminddb.open_database(str(mmdb_path)) as reader:
        for net, data in reader:
            asn = str(data.get("autonomous_system_number", ""))
            records.append(Record(network=str(net), source="geolite2", asn=asn))
    return records


def parse_dbip_city(mmdb_path: Path) -> list[Record]:
    """解析 DB-IP city-lite.mmdb。"""
    import maxminddb
    records: list[Record] = []
    with maxminddb.open_database(str(mmdb_path)) as reader:
        for net, data in reader:
            country = (data.get("country") or {}).get("iso_code", "")
            subs = data.get("subdivisions") or [{}]
            province = (subs[0].get("names") or {}).get("zh-CN", "") if subs else ""
            city = ((data.get("city") or {}).get("names") or {}).get("zh-CN", "")
            records.append(Record(
                network=str(net),
                source="dbip",
                country=country,
                province=normalize_province(province),
                city=normalize_city(city),
            ))
    return records


def parse_rir_delegated(path: Path) -> list[Record]:
    """解析 RIR delegated-* 文本，提取 ipv4 网段的国家归属。"""
    records: list[Record] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 7:
                continue
            registry, cc, typ, start, value, _date, status = parts[:7]
            if typ != "ipv4" or status != "allocated" and status != "assigned":
                # 只要 allocated / assigned
                pass
            if typ != "ipv4":
                continue
            try:
                count = int(value)
            except ValueError:
                continue
            if count <= 0:
                continue
            # 计算 CIDR
            net = ipaddress.summarize_address_range(
                ipaddress.IPv4Address(start),
                ipaddress.IPv4Address(int(ipaddress.IPv4Address(start)) + count - 1),
            ).__next__()
            records.append(Record(
                network=str(net),
                source="rir",
                country=normalize_country(cc),
            ))
    return records


def extract_tarball(tar_gz: Path, out_dir: Path) -> Path:
    """解压 tar.gz，返回解压目录。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_gz, "r:gz") as tar:
        tar.extractall(out_dir)
    return out_dir


def extract_mmdb_from_tar(tar_gz: Path, keyword: str, out_dir: Path) -> Path:
    """从 tar.gz 中找出含 keyword 的 .mmdb 文件并解压，返回路径。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_gz, "r:gz") as tar:
        for m in tar.getmembers():
            if m.name.endswith(".mmdb") and keyword in m.name:
                tar.extract(m, out_dir)
                return out_dir / m.name
    raise FileNotFoundError(f"tar 中未找到 {keyword} 的 mmdb")


def gunzip(gz_path: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(gz_path, "rb") as f_in, open(out_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    return out_path

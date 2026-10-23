"""输出模块：将融合结果写出为 mmdb 与 CSV。

mmdb 使用 `mmdb_writer`（MaxMind DB 官方兼容的 Python 写库）生成，
字段对齐 GeoLite2-City 结构，并追加自定义扩展字段
（confidence、isp、network_type）。
"""

from __future__ import annotations

import csv
from pathlib import Path

from mmdb_writer import MMDBWriter, MmdbU16, MmdbU32

from ..merge.vote import MergedRecord

# ISO 3166-1 alpha-2 → 中文名（节选，覆盖主要国家）
ISO_TO_CN = {
    "CN": "中国", "HK": "香港", "MO": "澳门", "TW": "台湾",
    "US": "美国", "JP": "日本", "KR": "韩国", "SG": "新加坡",
    "DE": "德国", "FR": "法国", "GB": "英国", "RU": "俄罗斯",
    "AU": "澳大利亚", "CA": "加拿大", "IN": "印度", "VN": "越南",
    "TH": "泰国", "MY": "马来西亚", "ID": "印度尼西亚", "PH": "菲律宾",
}


def _names(zh: str, en: str = "") -> dict:
    """构造 names 字典。若无 en，则以中文名兜底，保证各语言客户端 .name 可取值。"""
    d = {}
    if zh:
        d["zh-CN"] = zh
    if en:
        d["en"] = en
    elif zh:
        d["en"] = zh  # 兜底：en 键也用中文，避免部分客户端返回 None
    return d


def to_mmdb_dict(m: MergedRecord) -> dict:
    """转换为 GeoLite2-City 兼容结构 + 扩展字段。"""
    country_name = ISO_TO_CN.get(m.country, m.country)
    node: dict = {
        "country": {
            "iso_code": m.country,
            "names": _names(country_name, m.country),
        },
        "city": {"names": _names(m.city)} if m.city else {},
        # accuracy_radius 用 uint16（Java geoip2 Location 期望 uint16）
        "location": {"accuracy_radius": MmdbU16(0)},
    }
    # subdivisions 为空时不输出该键：PHP geoip2 官方库遇到空数组会取
    # count-1 = -1 下标导致报错（Go/Python 能容忍，但 PHP 不行）。
    if m.province:
        node["subdivisions"] = [{"names": _names(m.province)}]
    # 扩展字段：放在 traits 下
    node["traits"] = {
        "isp": m.isp or "",
        "organization": m.isp or "",
        "network_type": m.network_type or "isp",
        # confidence 用 uint16
        "confidence": MmdbU16(m.confidence),
    }
    if m.asn:
        try:
            # autonomous_system_number 必须用 uint32（Java geoip2 期望 uint32，
            # 写成 uint16 会导致反序列化 NullPointerException）
            node["traits"]["autonomous_system_number"] = MmdbU32(int(m.asn))
        except ValueError:
            pass
    return node


def write_mmdb(records: list[MergedRecord], out_path: Path,
               ip_version: int = 4) -> Path:
    """写出 mmdb 文件（ip_version 固定为 4，IPv6 后续扩展）。"""
    from netaddr import IPSet
    out_path.parent.mkdir(parents=True, exist_ok=True)

    writer = MMDBWriter(
        ip_version=ip_version,
        # 必须用 GeoLite2-City 标准名称，Go/Java 等语言的 geoip2 官方库
        # 会严格校验 database_type，自定义名称会被拒绝打开。
        database_type="GeoLite2-City",
        # int_type 用默认 auto：具体字段类型已通过 MmdbU16/MmdbU32 显式标注
        # （accuracy_radius/confidence→u16，autonomous_system_number→u32）。
        languages=["zh-CN", "en"],
        description={
            "en": "ipgeo multi-source merged IP geolocation database",
            "zh-CN": "ipgeo 多源融合 IP 地理位置数据库",
        },
    )
    for m in records:
        net = _to_netaddr(m.network, ip_version)
        if net is None:
            continue
        writer.insert_network(IPSet([net]), to_mmdb_dict(m))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer.to_db_file(str(out_path))
    return out_path


def _to_netaddr(cidr: str, ip_version: int):
    from netaddr import IPNetwork
    try:
        net = IPNetwork(cidr)
    except Exception:  # noqa: BLE001
        return None
    if net.version != ip_version:
        return None
    return net


def write_csv(records: list[MergedRecord], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["network", "country", "province", "city", "isp", "asn",
                  "network_type", "confidence", "sources"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for m in sorted(records, key=lambda x: x.network):
            w.writerow(m.to_dict())
    return out_path

"""ipgeo 公共工具：IP 前缀解析、CIDR 工具、字段归一化。"""

from __future__ import annotations

import ipaddress
from typing import Optional


def parse_network(cidr: str) -> Optional[ipaddress.IPv4Network]:
    """解析 CIDR 字符串为 IPv4Network，失败返回 None。"""
    try:
        # 部分数据源用 "1.2.3.4 - 1.2.3.255" 起止格式
        cidr = cidr.strip()
        if " - " in cidr:
            start, end = cidr.split(" - ", 1)
            return ipaddress.summarize_address_range(
                ipaddress.IPv4Address(start.strip()),
                ipaddress.IPv4Address(end.strip()),
            ).__next__()
        return ipaddress.ip_network(cidr, strict=False)
    except (ValueError, AttributeError):
        return None


def ip_to_int(ip: str) -> int:
    return int(ipaddress.IPv4Address(ip))


def normalize_country(name: str) -> str:
    """统一国家名（返回 ISO 3166-1 alpha-2 或中文名，尽力而为）。"""
    if not name:
        return ""
    name = name.strip()
    # 常见中文名映射为 ISO 码（节选，可扩展）
    cn_to_iso = {
        "中国": "CN", "香港": "HK", "澳门": "MO", "台湾": "TW",
        "美国": "US", "日本": "JP", "韩国": "KR", "新加坡": "SG",
        "德国": "DE", "法国": "FR", "英国": "GB", "俄罗斯": "RU",
        "澳大利亚": "AU", "加拿大": "CA", "印度": "IN", "越南": "VN",
        "泰国": "TH", "马来西亚": "MY", "印度尼西亚": "ID", "菲律宾": "PH",
    }
    if name in cn_to_iso:
        return cn_to_iso[name]
    # 已是 ISO 码则原样返回（大写）
    if len(name) == 2 and name.isalpha():
        return name.upper()
    return name


def normalize_province(name: str) -> str:
    """归一化省份名：去掉"省/市/自治区/特别行政区"等后缀。"""
    if not name:
        return ""
    name = name.strip()
    for suf in ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区",
                "自治区", "省", "市"):
        if name.endswith(suf) and len(name) > len(suf):
            name = name[: -len(suf)]
    return name


def normalize_city(name: str) -> str:
    """归一化城市名。"""
    if not name:
        return ""
    name = name.strip()
    for suf in ("市", "地区", "自治州", "盟"):
        if name.endswith(suf) and len(name) > len(suf):
            name = name[: -len(suf)]
    return name

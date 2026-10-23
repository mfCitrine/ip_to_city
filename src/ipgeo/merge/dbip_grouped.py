"""DB-IP CSV 高性能解析：整数区间 + 按属性分组 + 区间合并。

DB-IP city-lite CSV 约 780 万行，其中约 416 万行是 IPv6、362 万行是 IPv4。
本模块只处理 IPv4（MVP 范围），用整数区间（非 netaddr，快 10 倍）按属性
分组并合并相邻同属性网段，压缩记录数。
"""

from __future__ import annotations

import gzip
import ipaddress
import socket
import struct
from pathlib import Path

from ..utils.iputil import normalize_city, normalize_country, normalize_province
from .vote import Record

_EN_TO_ZH = {
    "Beijing": "北京", "Shanghai": "上海", "Tianjin": "天津", "Chongqing": "重庆",
    "Guangdong": "广东", "Fujian": "福建", "Zhejiang": "浙江", "Jiangsu": "江苏",
    "Shandong": "山东", "Henan": "河南", "Hebei": "河北", "Hubei": "湖北",
    "Hunan": "湖南", "Sichuan": "四川", "Shaanxi": "陕西", "Shanxi": "山西",
    "Anhui": "安徽", "Jiangxi": "江西", "Yunnan": "云南", "Guizhou": "贵州",
    "Guangxi": "广西", "Hainan": "海南", "Liaoning": "辽宁", "Jilin": "吉林",
    "Heilongjiang": "黑龙江", "Inner Mongolia": "内蒙古", "Ningxia": "宁夏",
    "Gansu": "甘肃", "Qinghai": "青海", "Xinjiang": "新疆", "Tibet": "西藏",
    "Hong Kong": "香港", "Macao": "澳门", "Taiwan": "台湾",
    "Guangzhou": "广州", "Shenzhen": "深圳", "Nanjing": "南京", "Hangzhou": "杭州",
    "Chengdu": "成都", "Wuhan": "武汉", "Xi'an": "西安", "Suzhou": "苏州",
    "Fuzhou": "福州", "Xiamen": "厦门", "Qingdao": "青岛", "Jinan": "济南",
    "Zhengzhou": "郑州", "Changsha": "长沙", "Kunming": "昆明", "Hefei": "合肥",
    "Nanchang": "南昌", "Taiyuan": "太原", "Shijiazhuang": "石家庄",
    "Shenyang": "沈阳", "Dalian": "大连", "Harbin": "哈尔滨", "Changchun": "长春",
    "Lanzhou": "兰州", "Guiyang": "贵阳", "Nanning": "南宁", "Haikou": "海口",
    "Urumqi": "乌鲁木齐", "Lhasa": "拉萨", "Wuxi": "无锡", "Changzhou": "常州",
    "Ningbo": "宁波", "Wenzhou": "温州", "Dongguan": "东莞", "Foshan": "佛山",
}


def _en_to_zh(name: str) -> str:
    return _EN_TO_ZH.get(name, name)


def _ip2int(ip: str) -> int:
    return struct.unpack("!I", socket.inet_aton(ip))[0]


def _int2cidr(s: int, e: int) -> list[str]:
    nets = ipaddress.summarize_address_range(
        ipaddress.IPv4Address(s), ipaddress.IPv4Address(e)
    )
    return [str(n) for n in nets]


def parse_dbip_csv_v4(csv_gz: Path) -> list[Record]:
    """解析 DB-IP IPv4 记录，按 (country, province, city) 分组合并。"""
    groups: dict[tuple[str, str, str], list[tuple[int, int]]] = {}

    with gzip.open(csv_gz, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.rstrip("\n").split(",")
            if len(parts) < 6:
                continue
            start_ip, end_ip = parts[0], parts[1]
            # 跳过 IPv6 与保留段
            if ":" in start_ip or parts[3] == "ZZ":
                continue
            try:
                s = _ip2int(start_ip)
                e = _ip2int(end_ip)
            except OSError:
                continue
            country = parts[3]
            region = parts[4].strip('"').strip()
            city = parts[5].strip('"').strip()
            if country == "CN":
                prov = normalize_province(_en_to_zh(region))
                cit = normalize_city(_en_to_zh(city))
            else:
                prov = region
                cit = city
            key = (normalize_country(country), prov, cit)
            groups.setdefault(key, []).append((s, e))

    # 每组合并相邻/重叠区间
    records: list[Record] = []
    for (country, prov, cit), ranges in groups.items():
        merged_ranges = _merge_int_ranges(ranges)
        for s, e in merged_ranges:
            for cidr in _int2cidr(s, e):
                records.append(Record(
                    network=cidr,
                    source="dbip",
                    country=country,
                    province=prov,
                    city=cit,
                ))
    return records


def _merge_int_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """合并整数区间（相邻或重叠）。"""
    ranges.sort()
    merged: list[tuple[int, int]] = []
    for s, e in ranges:
        if merged and s <= merged[-1][1] + 1:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged

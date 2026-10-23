"""iptoasn.com IP→ASN→国家 索引（解决国家归属边界冲突的权威仲裁源）。

数据格式（tsv）：range_start \\t range_end \\t ASN \\t country_code \\t AS_description
加载为排序的整数区间列表，二分查找，O(log n)。
"""

from __future__ import annotations

import gzip
import socket
import struct
from pathlib import Path


def _ip2int(ip: str) -> int:
    return struct.unpack("!I", socket.inet_aton(ip))[0]


class IptoasnIndex:
    """iptoasn 索引：内存中排序区间 + 二分查询。"""

    def __init__(self, tsv_gz: Path):
        self._ranges: list[tuple[int, int, str, int, str]] = []
        self._load(tsv_gz)

    def _load(self, tsv_gz: Path):
        ranges: list[tuple[int, int, str, int, str]] = []
        with gzip.open(tsv_gz, "rt", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 5:
                    continue
                start_ip, end_ip, asn_s, country, desc = parts[:5]
                # 跳过 Not routed（ASN=0 / country=None）
                if asn_s == "0" or country == "None":
                    continue
                try:
                    s = _ip2int(start_ip)
                    e = _ip2int(end_ip)
                    asn = int(asn_s)
                except (OSError, ValueError):
                    continue
                ranges.append((s, e, country, asn, desc))
        ranges.sort(key=lambda x: x[0])
        self._ranges = ranges
        # 预提取 starts 数组供二分
        self._starts = [r[0] for r in ranges]

    def lookup(self, ip: str) -> tuple[str, int, str] | None:
        """返回 (country_code, asn, as_description)，未命中返回 None。"""
        ip_int = _ip2int(ip)
        import bisect
        idx = bisect.bisect_right(self._starts, ip_int) - 1
        if idx < 0:
            return None
        s, e, country, asn, desc = self._ranges[idx]
        if s <= ip_int <= e:
            return country, asn, desc
        return None

    def __len__(self):
        return len(self._ranges)


def load_index(tsv_gz: Path) -> IptoasnIndex:
    return IptoasnIndex(tsv_gz)

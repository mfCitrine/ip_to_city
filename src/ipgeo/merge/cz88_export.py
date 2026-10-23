"""纯真 QQWry 高效导出：遍历索引区拿段边界 + qqwry-py3 lookup 查归属。

纯真索引区每条 7 字节（起始IP 4字节小端 + 记录偏移 3字节小端）。
第 i 条段的覆盖范围 = [index[i].start, index[i+1].start - 1]。
用 qqwry-py3 的 lookup 查段起始 IP 的归属（快，约 5 秒/53 万次）。
"""

from __future__ import annotations

import ipaddress
import struct
from pathlib import Path

from ..utils.iputil import normalize_city, normalize_province
from ..download.cz88 import _split_location
from .vote import Record


def export_cn_records(db_path: Path) -> list[Record]:
    """遍历纯真索引区，导出中国区 IP 段为 Record 列表。"""
    import qqwry
    q = qqwry.QQwry()
    q.load_file(str(db_path))
    data = q.data
    first, last = struct.unpack("<II", data[:8])
    count = (last - first) // 7 + 1

    records: list[Record] = []
    prev_start: int | None = None

    for i in range(count + 1):
        if i < count:
            pos = first + i * 7
            start_ip = struct.unpack("<I", data[pos:pos + 4])[0]
        else:
            start_ip = 0x100000000  # 最后一段延伸到末尾

        if prev_start is not None:
            seg_start = prev_start
            seg_end = start_ip - 1
            if seg_end >= seg_start:
                raw = q.lookup(str(ipaddress.IPv4Address(seg_start)))
                if raw:
                    loc, isp = raw
                    loc = (loc or "").replace("CZ88.NET", "").strip()
                    country, province, city = _split_location(loc)
                    # 国内段判定：明确 CN，或含省/市标记
                    if country == "CN" or "省" in loc or "市" in loc:
                        for cidr in _range_to_cidrs(seg_start, seg_end):
                            records.append(Record(
                                network=cidr,
                                source="cz88",
                                country="CN",
                                province=normalize_province(province),
                                city=normalize_city(city),
                                isp=(isp or "").replace("CZ88.NET", "").strip(),
                            ))

        prev_start = start_ip

    return records


def _range_to_cidrs(s: int, e: int) -> list[str]:
    nets = ipaddress.summarize_address_range(
        ipaddress.IPv4Address(s), ipaddress.IPv4Address(e)
    )
    return [str(n) for n in nets]

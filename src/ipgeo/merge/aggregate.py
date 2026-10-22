"""聚合器：把多源 Record 按前缀聚合，逐前缀投票融合，
并在写库前消解重叠前缀（细前缀优先，粗前缀挖掉被覆盖部分）。

关键：mmdb_writer 的 insert_network 是「后插入覆盖先插入」，不做 LPM 去重，
因此必须在写入前把重叠关系消解成互不重叠的网段集合。

重叠消解采用「按前缀长度分层 + 区间减法」的高效算法。
"""

from __future__ import annotations

import ipaddress
from bisect import bisect_right
from collections import defaultdict

from .vote import Record, MergedRecord, merge_records


def aggregate(records: list[Record]) -> list[MergedRecord]:
    """按网络前缀聚合记录并融合（同前缀的多源记录投票）。"""
    groups: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        groups[r.network].append(r)

    merged: list[MergedRecord] = []
    for net, recs in groups.items():
        merged.append(merge_records(recs))
    return merged


def _net_range(network: str) -> tuple[int, int, int]:
    """返回 (start_int, end_int, prefixlen)。"""
    n = ipaddress.ip_network(network, strict=False)
    return int(n.network_address), int(n.broadcast_address), n.prefixlen


def resolve_overlap(merged: list[MergedRecord]) -> list[MergedRecord]:
    """消解重叠前缀：更细（更长掩码）记录优先覆盖更粗记录。

    算法：
      1. 按前缀长度分层（长→短），细层先「占地」。
      2. 每层处理时，用更细层已占用的区间做减法，得到本层剩余的
         [start, end] 区间；每个剩余区间拆成若干 CIDR。
      3. 层内自底向上累积已占用区间。
    复杂度约 O(n log n)（每层的区间减法用有序占用列表 + 二分可优化，
    当前实现为线性扫描，对万级数据足够）。
    """
    if not merged:
        return []

    by_prefixlen: dict[int, list[MergedRecord]] = defaultdict(list)
    for m in merged:
        n = ipaddress.ip_network(m.network, strict=False)
        by_prefixlen[n.prefixlen].append(m)

    occupied: list[tuple[int, int]] = []  # 更细层已占用的 [start, end]
    result: list[MergedRecord] = []

    for plen in sorted(by_prefixlen.keys(), reverse=True):
        # 本层线段排序
        segs: list[tuple[int, int, MergedRecord]] = []
        for m in by_prefixlen[plen]:
            s, e, _ = _net_range(m.network)
            segs.append((s, e, m))
        segs.sort(key=lambda x: (x[0], x[1]))

        new_occupied: list[tuple[int, int]] = []
        for s, e, m in segs:
            # 减去更细层已占用区间
            for ps, pe in _subtract_ranges(s, e, occupied):
                for cidr in _range_to_cidrs(ps, pe):
                    result.append(_clone_with_network(m, cidr))
                    new_occupied.append((ps, pe))

        # 合并本层占用的区间
        occupied = _merge_ranges(occupied + new_occupied)

    result.sort(key=lambda x: _net_range(x.network))
    return result


def _subtract_ranges(s: int, e: int,
                     occ: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """从 [s, e] 中减去 occ（按 start 有序、互不重叠）里的区间。

    用二分定位第一个 end >= s 的区间，然后线性处理重叠部分。
    由于 occ 有序且互不重叠，重叠区间的数量通常很少。
    """
    # 二分：找到第一个 end >= s 的区间索引
    lo, hi = 0, len(occ)
    while lo < hi:
        mid = (lo + hi) // 2
        if occ[mid][1] < s:
            lo = mid + 1
        else:
            hi = mid
    # 从 lo 开始，处理所有 start <= e 的区间
    remaining = [(s, e)]
    i = lo
    while i < len(occ):
        os_, oe = occ[i]
        if os_ > e:
            break
        # os_ <= e 且 oe >= s（由 lo 保证后半段），必重叠
        new_remaining: list[tuple[int, int]] = []
        for rs, re_ in remaining:
            if oe < rs or os_ > re_:
                new_remaining.append((rs, re_))
            else:
                if rs < os_:
                    new_remaining.append((rs, os_ - 1))
                if re_ > oe:
                    new_remaining.append((oe + 1, re_))
        remaining = new_remaining
        if not remaining:
            return []
        i += 1
    return remaining


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """合并区间（输入可乱序）。"""
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged = [list(ranges[0])]
    for s, e in ranges[1:]:
        if s <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def _range_to_cidrs(s: int, e: int) -> list[str]:
    """整数起止区间 → CIDR 列表。"""
    nets = ipaddress.summarize_address_range(
        ipaddress.IPv4Address(s), ipaddress.IPv4Address(e)
    )
    return [str(n) for n in nets]


def _clone_with_network(m: MergedRecord, network: str) -> MergedRecord:
    """复制记录并替换 network 字段。"""
    return MergedRecord(
        network=network,
        country=m.country,
        province=m.province,
        city=m.city,
        isp=m.isp,
        asn=m.asn,
        network_type=m.network_type,
        confidence=m.confidence,
        sources=list(m.sources),
    )

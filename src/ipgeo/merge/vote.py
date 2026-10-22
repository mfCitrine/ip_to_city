"""融合引擎数据模型与多源投票、置信度打分、类型标注。

核心思路（见 docs/MERGE_ALGORITHM.md）：
  1. 各数据源解析为统一的 Record（前缀 + 国家/省/市 + 来源可信度）。
  2. 按前缀聚合，逐层（国家/省/市）投票。
  3. 按一致性计算置信度。
  4. 标注网络类型（isp/mobile/idc/vpn）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..utils.iputil import normalize_city, normalize_country, normalize_province

# 各数据源的基础可信度（0~1）
SOURCE_WEIGHT = {
    "rir": 0.98,      # 国家维度权威
    "geolite2": 0.85,  # 城市级主力，周更
    "dbip": 0.80,      # 城市级交叉
    "cz88": 0.70,      # 国内参考
}


@dataclass
class Record:
    """单个数据源对某个 IP 前缀的判定结果。"""
    network: str              # CIDR
    source: str               # rir / geolite2 / dbip / cz88
    country: str = ""         # ISO 3166-1 alpha-2
    province: str = ""        # 省/州（中文）
    city: str = ""            # 城市（中文）
    isp: str = ""             # 运营商
    asn: str = ""             # AS 号
    network_type: str = ""    # isp/mobile/idc/vpn


@dataclass
class MergedRecord:
    """融合后的最终记录。"""
    network: str
    country: str = ""
    province: str = ""
    city: str = ""
    isp: str = ""
    asn: str = ""
    network_type: str = "isp"
    confidence: int = 0
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "network": self.network,
            "country": self.country,
            "province": self.province,
            "city": self.city,
            "isp": self.isp,
            "asn": self.asn,
            "network_type": self.network_type,
            "confidence": self.confidence,
            "sources": ",".join(self.sources),
        }


def _vote(values: list[str], weights: list[float]) -> tuple[str, float, int]:
    """加权投票。返回 (获胜值, 归一化一致度, 参与投票的非空来源数)。"""
    if not values:
        return "", 0.0, 0
    tally: dict[str, float] = {}
    for v, w in zip(values, weights):
        if v:
            tally[v] = tally.get(v, 0.0) + w
    if not tally:
        return "", 0.0, 0
    winner = max(tally, key=tally.get)
    total = sum(tally.values())
    agree = tally[winner] / total  # 0~1，1 表示全部一致
    n = sum(1 for v in values if v)
    return winner, agree, n


def merge_records(records: list[Record]) -> MergedRecord:
    """对同一前缀的多源记录做投票融合。"""
    if not records:
        raise ValueError("empty records")

    net = records[0].network
    weights = [SOURCE_WEIGHT.get(r.source, 0.5) for r in records]

    # 先统一归一化，避免不同入口传入的原始值不一致
    norm_countries = [normalize_country(r.country) for r in records]
    norm_provinces = [normalize_province(r.province) for r in records]
    norm_cities = [normalize_city(r.city) for r in records]

    # 国家层
    country, c_agree, c_n = _vote(norm_countries, weights)
    # 省层
    province, p_agree, p_n = _vote(norm_provinces, weights)
    # 城市层
    city, ct_agree, ct_n = _vote(norm_cities, weights)
    # 运营商
    isp, _, _ = _vote([r.isp for r in records], weights)
    # ASN
    asn, _, _ = _vote([r.asn for r in records], weights)
    # 类型
    ntype, _, _ = _vote([r.network_type for r in records], weights)

    # 置信度打分
    confidence = _score_confidence(country, c_agree, c_n,
                                   province, p_agree, p_n,
                                   city, ct_agree, ct_n)

    return MergedRecord(
        network=net,
        country=country,
        province=province,
        city=city,
        isp=isp,
        asn=asn,
        network_type=ntype or "isp",
        confidence=confidence,
        sources=sorted({r.source for r in records}),
    )


def _score_confidence(country, c_agree, c_n,
                      province, p_agree, p_n,
                      city, ct_agree, ct_n) -> int:
    """按一致性计算 0~100 的置信度（见设计文档）。"""
    # 国家层：有 RIR 或多数一致 → 高
    if not country:
        return 0
    # 省市层一致性权重更大
    if province and city:
        if p_n >= 3 and ct_n >= 2 and p_agree > 0.9 and ct_agree > 0.9:
            return 90
        if p_n >= 2 and ct_n >= 2:
            return 80
        if p_n >= 1:
            return 60
    elif province:
        if p_n >= 3 and p_agree > 0.9:
            return 85
        if p_n >= 2:
            return 75
        return 55
    # 只有国家
    if c_n >= 3 and c_agree > 0.9:
        return 99
    if c_n >= 2:
        return 95
    return 90


def infer_network_type(records: list[Record]) -> str:
    """根据 ASN/来源特征推断网络类型。"""
    # 简单启发式：后续可接入 ASN→类型 映射表增强
    for r in records:
        if r.network_type:
            return r.network_type
    return "isp"

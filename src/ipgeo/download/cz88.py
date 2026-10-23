"""纯真 IP 库（QQWry.Dat）解析器（仅内部交叉校验，不直接再分发）。

使用 qqwry-py3 库解析，把纯真数据转为统一的 Record。
纯真返回格式：(国家省市区连写, 运营商/机构详情)。

注意：纯真数据的定位是「内部参考」，其数据不打包进 GitHub 仓库或 Release。
"""

from __future__ import annotations

from pathlib import Path

from ..utils.iputil import normalize_city, normalize_country, normalize_province
from ..merge.vote import Record


def locate_cz88(out_dir: Path) -> Path | None:
    """查找本地已放置的 QQWry.Dat。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("QQWry.Dat", "qqwry.dat", "qqwry.db"):
        p = out_dir / name
        if p.exists():
            return p
    return None


def _split_location(loc: str) -> tuple[str, str, str]:
    """把 '江苏省南京市' / '美国加利福尼亚州...' 拆成 (国家, 省, 市)。"""
    loc = (loc or "").replace("CZ88.NET", "").strip()
    if not loc:
        return "", "", ""
    # 直辖市：北京/上海/天津/重庆，province 与 city 都取直辖市名
    for dc in ("北京", "上海", "天津", "重庆"):
        if loc.startswith(dc):
            rest = loc[len(dc):]
            # 去掉开头的"市"字，剩余是区/县
            if rest.startswith("市"):
                rest = rest[1:]
            return "CN", dc + "市", rest
    # 国内：以省开头
    for p in ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区",
              "自治区", "省"):
        idx = loc.find(p)
        if 0 < idx <= 6:
            province = loc[:idx + len(p)]
            city = loc[idx + len(p):]
            return "CN", province, city
    # 国外：国家名开头（无省后缀）
    return loc, "", ""


def parse_cz88(db_path: Path) -> "QQWryAdapter":
    """加载纯真库，返回适配器（懒查询）。"""
    import qqwry
    q = qqwry.QQwry()
    if not q.load_file(str(db_path)):
        raise RuntimeError(f"纯真库加载失败: {db_path}")
    return QQWryAdapter(q)


class QQWryAdapter:
    """封装 qqwry-py3，提供 lookup → Record 的能力。"""

    def __init__(self, q):
        self._q = q

    def lookup_record(self, ip: str) -> Record:
        r = self._q.lookup(ip)
        if not r:
            return Record(network=f"{ip}/32", source="cz88")
        loc, isp = r
        country, province, city = _split_location(loc)
        return Record(
            network=f"{ip}/32",
            source="cz88",
            country=normalize_country(country),
            province=normalize_province(province),
            city=normalize_city(city),
            isp=(isp or "").replace("CZ88.NET", "").strip(),
        )

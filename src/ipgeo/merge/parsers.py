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


def parse_dbip_csv(csv_gz: Path) -> list[Record]:
    """解析 DB-IP city-lite CSV（更高效，推荐用于大库）。

    CSV 格式：start_ip,end_ip,continent,country,region,city,lat,lng
    其中 region/city 为英文，需经 _en_to_zh 转中文（仅中国区）。
    """
    import gzip
    records: list[Record] = []
    with gzip.open(csv_gz, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            start_ip, end_ip, _cont, country, region, city = parts[:6]
            # 跳过保留段（country == ZZ）
            if country == "ZZ":
                continue
            # 起止 IP → CIDR 列表
            try:
                nets = ipaddress.summarize_address_range(
                    ipaddress.IPv4Address(start_ip.strip()),
                    ipaddress.IPv4Address(end_ip.strip()),
                )
            except ValueError:
                continue
            prov = _en_to_zh(region.strip()) if country == "CN" else region.strip()
            cit = _en_to_zh(city.strip()) if country == "CN" else city.strip()
            for net in nets:
                records.append(Record(
                    network=str(net),
                    source="dbip",
                    country=normalize_country(country),
                    province=normalize_province(prov),
                    city=normalize_city(cit),
                ))
    return records


# 中国省/市英文 → 中文（节选常见）
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


def parse_dbip_asn(mmdb_path: Path) -> list[Record]:
    """解析 DB-IP asn-lite.mmdb，提取 ASN 与运营商。"""
    import maxminddb
    records: list[Record] = []
    with maxminddb.open_database(str(mmdb_path)) as reader:
        for net, data in reader:
            asn = str(data.get("autonomous_system_number", ""))
            as_org = data.get("autonomous_system_organization", "")
            records.append(Record(
                network=str(net),
                source="dbip",
                asn=asn,
                isp=as_org,
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

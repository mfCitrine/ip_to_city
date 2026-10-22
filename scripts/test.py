"""冒烟测试：验证融合逻辑与 mmdb 读写。

用法：python scripts/test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ipgeo.merge.vote import Record, merge_records  # noqa: E402


def test_merge_vote():
    # 多源一致 → 高置信
    recs = [
        Record("114.114.114.0/24", "rir", country="CN"),
        Record("114.114.114.0/24", "geolite2", country="CN",
               province="江苏省", city="南京市", isp="中国电信"),
        Record("114.114.114.0/24", "dbip", country="CN",
               province="江苏省", city="南京市"),
    ]
    m = merge_records(recs)
    assert m.country == "CN", m.country
    assert m.province == "江苏", m.province
    assert m.city == "南京", m.city
    assert m.confidence >= 80, m.confidence
    print(f"[ok] 多源一致融合：conf={m.confidence}, {m.country}/{m.province}/{m.city}")


def test_merge_conflict():
    # 国家冲突时 RIR 权重更高
    recs = [
        Record("8.8.8.0/24", "rir", country="US"),
        Record("8.8.8.0/24", "dbip", country="CN"),
    ]
    m = merge_records(recs)
    assert m.country == "US", m.country
    print(f"[ok] 冲突时 RIR 胜出：{m.country}")


def test_mmdb_roundtrip():
    import maxminddb
    from ipgeo.output.writer import write_mmdb
    from tempfile import TemporaryDirectory

    recs = [
        Record("114.114.114.0/24", "rir", country="CN"),
        Record("114.114.114.0/24", "geolite2", country="CN",
               province="江苏省", city="南京市", isp="中国电信"),
        Record("114.114.114.0/24", "dbip", country="CN",
               province="江苏省", city="南京市"),
    ]
    merged = [merge_records(recs)]
    with TemporaryDirectory() as d:
        p = Path(d) / "test.mmdb"
        write_mmdb(merged, p)
        with maxminddb.open_database(str(p)) as reader:
            data = reader.get("114.114.114.114")
            assert data["country"]["iso_code"] == "CN"
            assert data["traits"]["confidence"] >= 80
            assert data["traits"]["isp"] == "中国电信"
    print("[ok] mmdb 往返读写正确")


if __name__ == "__main__":
    test_merge_vote()
    test_merge_conflict()
    test_mmdb_roundtrip()
    print("\n全部测试通过 ✓")

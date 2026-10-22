"""纯真 IP 库下载器（仅内部交叉校验，不直接再分发）。

纯真免费版需要到 cz88.net 手动下载 QQWry.Dat。
由于下载地址不稳定且需人工操作，此模块提供占位与说明，
实际使用时请将 QQWry.Dat 放到 data/raw/cz88/ 目录。
"""

from __future__ import annotations

from pathlib import Path


def locate_cz88(out_dir: Path) -> Path | None:
    """查找本地已放置的 QQWry.Dat。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("QQWry.Dat", "qqwry.dat", "qqwry.db"):
        p = out_dir / name
        if p.exists():
            return p
    return None

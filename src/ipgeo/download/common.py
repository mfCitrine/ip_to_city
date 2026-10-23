"""通用下载器：带缓存、重试、校验。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import requests

DEFAULT_UA = "ipgeo/0.1 (+https://github.com/mfCitrine/ip_to_city)"


def download(url: str, dest: Path, retries: int = 3, timeout: int = 120,
             headers: dict | None = None) -> Path:
    """下载文件到 dest，带重试与简单缓存（已存在且大小>0 则跳过）。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    hdrs = {"User-Agent": DEFAULT_UA}
    if headers:
        hdrs.update(headers)

    last_err = None
    for i in range(retries):
        try:
            with requests.get(url, stream=True, timeout=timeout, headers=hdrs) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        f.write(chunk)
                os.replace(tmp, dest)
            return dest
        except Exception as e:  # noqa: BLE001
            last_err = e
            if i < retries - 1:
                continue
    raise RuntimeError(f"下载失败 {url}: {last_err}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()

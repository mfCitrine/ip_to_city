# 数据源说明

本项目融合以下公开数据源。每个数据源对应一个下载器，位于 `src/ipgeo/download/`。

## 已接入

| 数据源 | 精度 | 更新 | License | 用途 | 下载器 |
|---|---|---|---|---|---|
| RIR 分配数据 | 国家（权威） | 实时 | 公共 | 国家维度地基 | `rir.py` |
| MaxMind GeoLite2 | 国家准/城市中 | 周 | CC BY-SA 4.0 + EULA | 城市级主力 | `geolite2.py` |
| DB-IP | 国家/城市 | 月 | CC BY 4.0 | 城市级交叉验证 | `dbip.py` |
| 纯真 IP 库 | 国内省市 | 不定期 | 参考 | 国内交叉校验（不直接分发） | `cz88.py` |

## 计划接入

| 数据源 | 精度 | 用途 |
|---|---|---|
| BGP/ASN（RIPE RIS / RouteViews） | 路由级 | 拓扑定位、ASN 归属 |
| RDNS 反查 | 主机名地名 | 机房/城市线索 |
| IPinfo Lite | 国家+ASN | ASN 维度 |

## 关键约束（务必遵守）

1. **GeoLite2 EULA**：新版本发布后 30 天内删除旧版本数据库；每次下载需 license key。
2. **署名**：README 和分发物中必须保留各数据源署名（见 LICENSE-DATA）。
3. **再分发协议**：融合后整体以 CC BY-SA 4.0 发布。

## 下载前准备

- MaxMind GeoLite2 需要注册账号并获取 License Key：
  1. 注册 https://www.maxmind.com/en/geolite2/signup
  2. 获取 Account ID 与 License Key
  3. 写入 `scripts/.env`（见 `scripts/.env.example`）

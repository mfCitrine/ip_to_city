# 数据源说明

本项目融合以下公开数据源。每个数据源对应一个下载器，位于 `src/ipgeo/download/`。

## 融合策略（分层）

ipgeo 采用**分层融合**策略，而不是简单地把所有源混在一起投票：

- **中国区**：以纯真 IP 库为主（国内省市区精度最高），DB-IP 中国部分作为交叉校验。
- **非中国区**：以 DB-IP 为主（全球城市级，CC BY 4.0 可再分发）。
- **国家维度**：RIR 分配数据（APNIC/ARIN 等）作为权威地基。
- **GeoLite2**：作为海外环境（GitHub Actions）下的额外交叉验证源。

## 已接入

| 数据源 | 精度 | 更新 | License | 用途 | 国内可下载 |
|---|---|---|---|---|---|
| RIR 分配数据 | 国家（权威） | 实时 | 公共 | 国家维度地基 | ✅ |
| DB-IP Lite | 全球城市级 | 月 | CC BY 4.0 | 非中国区主力 | ✅ |
| 纯真 IP 库 | 国内省市区（精细） | 不定期 | 参考（不直接分发） | 中国区主力 | ✅ |
| iptoasn.com | IP→ASN→国家 | 日 | 免费（署名） | 国家归属仲裁 | 需代理 |
| MaxMind GeoLite2 | 国家准/城市中 | 周 | CC BY-SA 4.0 + EULA | 交叉验证 | ❌ 451 |

## 关键约束（务必遵守）

1. **GeoLite2 451 限制**：MaxMind 因美国「批量敏感数据出境」法规，禁止从中国大陆下载 GeoLite2（返回 HTTP 451）。需在海外环境（GitHub Actions runner）下载。
2. **GeoLite2 EULA**：新版本发布后 30 天内删除旧版本数据库。
3. **纯真数据**：License 不允许直接打包进开源仓库再分发，仅作**本地融合校验**，不提交、不发布原始 qqwry.dat。
4. **署名**：README 和分发物中必须保留各数据源署名（见 LICENSE-DATA）。
5. **再分发协议**：融合后整体以 CC BY-SA 4.0 发布。

## 下载前准备

- DB-IP 和 RIR：无需凭证，国内可直接下载。
- 纯真：手动下载 `QQWry.Dat`（https://www.cz88.net/）放到 `data/raw/cz88/`。
- GeoLite2：需注册 MaxMind 账号（https://www.maxmind.com/en/geolite2/signup）获取 Account ID + License Key，写入 `scripts/.env`。因 451 限制，实际下载由 GitHub Actions（海外）完成。

## 计划接入

| 数据源 | 精度 | 用途 |
|---|---|---|
| BGP/ASN（RIPE RIS / RouteViews） | 路由级 | 拓扑定位、ASN 归属 |
| RDNS 反查 | 主机名地名 | 机房/城市线索 |
| IPinfo Lite | 国家+ASN | ASN 维度 |

# 贡献指南

感谢你为 ipgeo 贡献！本项目欢迎两类贡献：**代码** 和 **数据订正**。

## 数据订正（最重要）

IP 库的核心价值在于"准"。如果你发现某个 IP 段定位错误，请通过以下任一方式提交：

### 方式一：提交 Issue（推荐）

创建 Issue，使用 `IP 订正` 模板，提供：

1. 有问题的 IP 或 IP 段（如 `114.114.114.0/24`）
2. 当前错误的位置
3. 正确的位置（国家/省/市/运营商）
4. 证据（如 traceroute 结果、运营商公告、你自己就是这个 IP 的用户等）

### 方式二：直接提交 PR

编辑 `data/corrections.csv`，格式：

```csv
network,country,province,city,isp,source,evidence,date
114.114.114.0/24,中国,江苏,南京,中国电信,manual,traceroute,2026-10-22
```

每行一个网段，`network` 用 CIDR 格式。我们会定期把人工订正合并进库。

## 代码贡献

1. Fork 本仓库，创建 feature 分支。
2. 核心融合逻辑位于 `src/ipgeo/merge/`。
3. 提交前运行 `python scripts/test.py` 确保测试通过。
4. 提交 PR，描述清楚改动与动机。

## 数据源接入

如需接入新的数据源，请在 `src/ipgeo/download/` 下新增下载器，并在 `docs/DATA_SOURCES.md` 中登记其 License 与署名要求。

## 行为准则

请保持友善、专业。IP 定位数据涉及隐私，禁止将本库用于违法、侵权或侵犯他人隐私的用途。

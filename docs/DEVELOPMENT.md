# 开发指南

## 环境准备

```bash
# 1. 克隆仓库
git clone https://github.com/mfCitrine/ip_to_city.git
cd ipgeo

# 2. 创建虚拟环境并安装依赖
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. 配置数据源凭证（仅 GeoLite2 需要）
cp scripts/.env.example scripts/.env
# 编辑 .env，填入 MaxMind 的 Account ID 和 License Key
```

## 获取 MaxMind GeoLite2 凭证（免费）

1. 注册 https://www.maxmind.com/en/geolite2/signup
2. 登录后在 "Manage License Keys" 创建 License Key
3. 把 Account ID 和 License Key 填入 `scripts/.env`

> 其它数据源（RIR、DB-IP）无需凭证，直接下载。

## 运行 Pipeline

```bash
# 全流程：下载 → 解析 → 融合 → 输出
python scripts/run_pipeline.py

# 仅下载
python scripts/run_pipeline.py --download-only

# 仅构建（数据已下载）
python scripts/run_pipeline.py --build-only
```

输出文件：
- `data/release/ipgeo-city.mmdb` — 主数据库（mmdb 格式）
- `data/release/ipgeo-city.csv` — 可读的 CSV 版本

## 运行测试

```bash
python scripts/test.py
```

## 目录结构速览

```
src/ipgeo/
├── download/       # 数据源下载器（rir/geolite2/dbip/cz88）
├── merge/          # 融合引擎（vote/aggregate/parsers）
├── output/         # mmdb + csv 输出
└── utils/          # IP/CIDR 工具
```

## 关键设计文档

- [数据源说明](docs/DATA_SOURCES.md)
- [融合算法](docs/MERGE_ALGORITHM.md)
- [贡献指南](../CONTRIBUTING.md)

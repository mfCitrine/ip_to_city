# ipgeo — 多源融合的高精度开源 IP 地理位置库

> 一个**多源交叉验证、带置信度、社区可校正、周更**的高精度开源 IP 库。
> 中国区精细，全球覆盖，天然支持 Go / Java / PHP / Python。

[![License: CC BY-SA 4.0 (data)](https://img.shields.io/badge/License_Data-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
[![License: MIT (code)](https://img.shields.io/badge/License_Code-MIT-blue.svg)](LICENSE-CODE)

---

## 为什么是 ipgeo？

市面上的开源 IP 库（如 ip2region、纯真免费版）普遍存在一个共同问题：**数据同源、纯静态标注、更新滞后**，导致同一个地区反复出错。ipgeo 换了一套方法论：

| 维度 | 传统开源库 | ipgeo |
|---|---|---|
| 数据来源 | 单一渠道（纯真等） | **RIR + GeoLite2 + DB-IP + 纯真 多源融合** |
| 定位方式 | 静态手工标注 | **多源投票 + BGP/ASN 拓扑 + RDNS** |
| 置信度 | ❌ 无 | ✅ 每条记录附带 confidence |
| 更新频率 | 季度级 | **周更（GitHub Actions 自动发布）** |
| 人工订正 | ❌ 无 | ✅ 社区校正闭环 |
| 精度承诺 | 一刀切 | **按网络类型诚实承诺**（移动/家宽/IDC 区分） |

## 特性

- **分层多源融合**：中国区用纯真（省市区最准），非中国区用 DB-IP（全球城市级），国家维度用 RIR 权威数据，各取所长而非简单混用。
- **置信度字段**：每条结果附 `confidence`（0~100），让你知道"这条数据有多可信"。
- **IP 类型标注**：区分 `mobile`（移动蜂窝）、`isp`（家宽）、`idc`（机房/云）、`vpn`（代理），并据此给出合理的精度承诺。
- **多语言开箱即用**：采用标准 **MaxMind mmdb 格式**，Go / Java / PHP / Python 用官方库直接读取，无需自研 SDK。
- **合规可再分发**：数据采用 CC BY-SA 4.0，代码采用 MIT，各上游数据源均署名回链。

## 快速开始

### 1. 下载数据

到 [Releases](https://github.com/mfphp/ip_to_city/releases) 下载最新 `ipgeo-city.mmdb`。

### 2. 各语言接入

<details>
<summary>Go</summary>

```go
import "github.com/oschwald/geoip2-golang"

db, _ := geoip2.Open("ipgeo-city.mmdb")
defer db.Close()

record, _ := db.City(net.ParseIP("114.114.114.114"))
fmt.Println(record.Country.Names["zh-CN"], record.City.Names["zh-CN"])
// 置信度通过 Subdivisions[0].Names 之外的扩展字段读取，见 sdk/go/README.md
```

</details>

<details>
<summary>Java</summary>

```java
import com.maxmind.geoip2.DatabaseReader;
import java.net.InetAddress;

try (DatabaseReader reader = new DatabaseReader.Builder(
        new File("ipgeo-city.mmdb")).build()) {
    CityResponse r = reader.city(InetAddress.getByName("114.114.114.114"));
    System.out.println(r.getCountry().getName() + " " + r.getCity().getName());
}
```

</details>

<details>
<summary>PHP</summary>

```php
require 'vendor/autoload.php';
use GeoIp2\Database\Reader;

$reader = new Reader('ipgeo-city.mmdb');
$record = $reader->city('114.114.114.114');
echo $record->country->name . ' ' . $record->city->name;
```

</details>

<details>
<summary>Python</summary>

```python
import geoip2.database

reader = geoip2.database.Reader('ipgeo-city.mmdb')
resp = reader.city('114.114.114.114')
print(resp.country.name, resp.city.name)
reader.close()
```

</details>

## 数据字段

每条 IP 记录包含：

| 字段 | 说明 |
|---|---|
| `country` | 国家（ISO 3166-1 + 中文名） |
| `subdivisions` | 省/州 |
| `city` | 城市 |
| `postal_code` | 邮编（如可用） |
| `location` | 经纬度、时区、精度半径（accuracy_radius） |
| `traits` | 网络类型（mobile/isp/idc/vpn）、ASN、运营商 |
| `confidence` | 置信度 0~100（自定义扩展字段） |

## 精度承诺（诚实说明）

IP 定位存在物理上限，我们按网络类型给出真实承诺：

| 网络类型 | 承诺精度 | 说明 |
|---|---|---|
| 家宽 / 企业专线 | 城市级 | 出口 IP 与物理位置基本一致 |
| 移动蜂窝（CGNAT） | 省级 | 全省共享出口网关，无法到城市 |
| IDC / 云 / VPN | 归属地（机房） | 标注为机房位置，非用户物理位置 |

## 项目结构

```
ipgeo/
├── src/ipgeo/           # 核心代码
│   ├── download/        # 数据获取
│   ├── merge/           # 融合引擎
│   ├── output/          # mmdb 输出
│   └── utils/           # 工具
├── sdk/                 # 多语言接入示例
├── data/                # 原始/中间/发布数据
├── docs/                # 文档
└── scripts/             # 脚本
```

## 如何贡献 / 订正数据

发现某个 IP 段定位错误？欢迎提交订正，见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 数据源与署名

本项目的 IP 数据融合自以下公开来源，感谢它们的贡献：

- **MaxMind GeoLite2** — [https://www.maxmind.com](https://www.maxmind.com)（CC BY-SA 4.0）
- **DB-IP** — [https://db-ip.com](https://db-ip.com)（CC BY 4.0）
- **RIR 分配数据**（APNIC / ARIN / RIPE NCC / LACNIC / AFRINIC）
- **纯真 IP 库** — 仅内部交叉校验，不直接再分发

## License

- **数据**：[CC BY-SA 4.0](LICENSE-DATA) — 使用/分发需署名并保持相同协议。
- **代码**：[MIT](LICENSE-CODE)

> ⚠️ 数据是派生作品，融合了 CC BY-SA（GeoLite2）与 CC BY（DB-IP）的数据，因此整体以 CC BY-SA 4.0 发布。请保留各上游署名。

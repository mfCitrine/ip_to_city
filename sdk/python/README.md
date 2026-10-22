# Python 接入示例

依赖：

```bash
pip install geoip2
```

代码：

```python
import geoip2.database

reader = geoip2.database.Reader('ipgeo-city.mmdb')
resp = reader.city('114.114.114.114')

print("国家:", resp.country.name)
print("省份:", resp.subdivisions.most_specific.name)
print("城市:", resp.city.name)
print("运营商:", resp.traits.isp)
reader.close()
```

> 注意：`confidence`、`network_type` 是 ipgeo 的**自定义扩展字段**，
> geoip2 标准模型（`Country`/`City`）不包含它们，需用底层 `maxminddb`
> 读取（推荐用于批量高性能场景）：

```python
import maxminddb

with maxminddb.open_database('ipgeo-city.mmdb') as reader:
    data = reader.get('114.114.114.114')
    print(data['country']['iso_code'])
    print(data['city']['names']['zh-CN'])
    print(data['traits']['isp'])
    print(data['traits']['confidence'])      # 置信度 0~100
    print(data['traits']['network_type'])    # isp/mobile/idc/vpn
```

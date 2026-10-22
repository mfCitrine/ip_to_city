# Go 接入示例

依赖：`github.com/oschwald/geoip2-golang`

```go
package main

import (
    "fmt"
    "net"
    "log"

    "github.com/oschwald/geoip2-golang"
)

func main() {
    db, err := geoip2.Open("ipgeo-city.mmdb")
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()

    ip := net.ParseIP("114.114.114.114")
    record, err := db.City(ip)
    if err != nil {
        log.Fatal(err)
    }

    // 国家/省/市（中文名在 names 的 zh-CN 键）
    fmt.Println("国家:", record.Country.Names["zh-CN"])
    if len(record.Subdivisions) > 0 {
        fmt.Println("省份:", record.Subdivisions[0].Names["zh-CN"])
    }
    fmt.Println("城市:", record.City.Names["zh-CN"])
    // 运营商与网络类型
    fmt.Println("运营商:", record.Traits.ISP)
}
```

安装依赖：

```bash
go get github.com/oschwald/geoip2-golang
```

> 说明：ipgeo 的 `confidence`、`network_type` 扩展字段存放在 mmdb 的
> `traits` 节点下，可通过 `record.Traits` 访问。

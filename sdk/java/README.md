# Java 接入示例

依赖（Maven）：

```xml
<dependency>
    <groupId>com.maxmind.geoip2</groupId>
    <artifactId>geoip2</artifactId>
    <version>4.2.0</version>
</dependency>
```

代码：

```java
import com.maxmind.geoip2.DatabaseReader;
import com.maxmind.geoip2.model.CityResponse;
import java.io.File;
import java.net.InetAddress;

public class Demo {
    public static void main(String[] args) throws Exception {
        File dbFile = new File("ipgeo-city.mmdb");
        try (DatabaseReader reader = new DatabaseReader.Builder(dbFile).build()) {
            InetAddress ip = InetAddress.getByName("114.114.114.114");
            CityResponse r = reader.city(ip);
            System.out.println("国家: " + r.getCountry().getName());
            System.out.println("省份: " + r.getMostSpecificSubdivision().getName());
            System.out.println("城市: " + r.getCity().getName());
            System.out.println("运营商: " + r.getTraits().getIsp());
        }
    }
}
```

> `confidence`、`network_type` 扩展字段可通过
> `r.getTraits().getJsonObject()` 获取原始 JSON 后读取。

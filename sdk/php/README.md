# PHP 接入示例

依赖（Composer）：

```bash
composer require geoip2/geoip2
```

代码：

```php
<?php
require 'vendor/autoload.php';

use GeoIp2\Database\Reader;

$reader = new Reader('ipgeo-city.mmdb');
$record = $reader->city('114.114.114.114');

echo "国家: " . $record->country->name . PHP_EOL;
echo "省份: " . $record->mostSpecificSubdivision->name . PHP_EOL;
echo "城市: " . $record->city->name . PHP_EOL;
echo "运营商: " . $record->traits->isp . PHP_EOL;
```

> `confidence`、`network_type` 扩展字段通过
> `$record->traits->raw['confidence']` 等原始数组访问。

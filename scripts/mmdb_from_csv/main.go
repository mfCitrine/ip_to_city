// mmdb_from_csv：读取 ipgeo-city.csv，用 MaxMind 官方 mmdbwriter 生成 mmdb。
//
// 为什么用 Go：Python mmdb_writer 建 650 万网段的树内存峰值过高，
// GitHub Actions runner OOM；Go 版本内存占用只有其零头且速度快一个量级。
//
// 记录结构与 src/ipgeo/output/writer.py 的 to_mmdb_dict 严格对齐：
//   - database_type = GeoLite2-City（各语言 geoip2 官方库强校验）
//   - accuracy_radius / confidence = uint16
//   - autonomous_system_number = uint32（Java 反序列化要求）
//   - subdivisions 为空时整体省略（PHP 空数组会崩）
//   - names：zh-CN 必有；en 键兜底（country 用 ISO 码，city/prov 用中文原值）
//
// 用法：go run . <input.csv> <output.mmdb>
package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"net/netip"
	"os"
	"strconv"

	"github.com/maxmind/mmdbwriter/v2"
	"github.com/maxmind/mmdbwriter/v2/mmdbtype"
)

// ISO 3166-1 alpha-2 → 中文名（与 writer.py 的 ISO_TO_CN 一致）
var isoToCN = map[string]string{
	"CN": "中国", "HK": "香港", "MO": "澳门", "TW": "台湾",
	"US": "美国", "JP": "日本", "KR": "韩国", "SG": "新加坡",
	"DE": "德国", "FR": "法国", "GB": "英国", "RU": "俄罗斯",
	"AU": "澳大利亚", "CA": "加拿大", "IN": "印度", "VN": "越南",
	"TH": "泰国", "MY": "马来西亚", "ID": "印度尼西亚", "PH": "菲律宾",
}

// names：zh-CN 必有；en = enName（空则兜底用 zhName），与 writer.py _names 对齐
func namesMap(zhName, enName string) mmdbtype.Map {
	m := mmdbtype.Map{}
	if zhName != "" {
		m[mmdbtype.String("zh-CN")] = mmdbtype.String(zhName)
	}
	if enName != "" {
		m[mmdbtype.String("en")] = mmdbtype.String(enName)
	} else if zhName != "" {
		m[mmdbtype.String("en")] = mmdbtype.String(zhName)
	}
	return m
}

func buildRecord(country, province, city, isp, asn, networkType string, confidence uint64) mmdbtype.Map {
	// country
	cnName := isoToCN[country]
	if cnName == "" {
		cnName = country
	}
	countryMap := mmdbtype.Map{
		mmdbtype.String("iso_code"): mmdbtype.String(country),
		mmdbtype.String("names"):    namesMap(cnName, country),
	}

	rec := mmdbtype.Map{
		mmdbtype.String("country"): countryMap,
		mmdbtype.String("location"): mmdbtype.Map{
			mmdbtype.String("accuracy_radius"): mmdbtype.Uint16(0),
		},
	}

	// city（空则省略整个键）
	if city != "" {
		rec[mmdbtype.String("city")] = mmdbtype.Map{
			mmdbtype.String("names"): namesMap(city, ""),
		}
	}

	// subdivisions（空则整体省略，PHP 兼容）
	if province != "" {
		rec[mmdbtype.String("subdivisions")] = mmdbtype.Slice{
			mmdbtype.Map{"names": namesMap(province, "")},
		}
	}

	// traits 扩展字段
	traits := mmdbtype.Map{
		mmdbtype.String("isp"):          mmdbtype.String(isp),
		mmdbtype.String("organization"): mmdbtype.String(isp),
		mmdbtype.String("network_type"): mmdbtype.String(networkType),
		mmdbtype.String("confidence"):   mmdbtype.Uint16(confidence),
	}
	if asn != "" {
		if v, err := strconv.ParseUint(asn, 10, 32); err == nil {
			traits[mmdbtype.String("autonomous_system_number")] = mmdbtype.Uint32(v)
		}
	}
	rec[mmdbtype.String("traits")] = traits
	return rec
}

func main() {
	if len(os.Args) != 3 {
		log.Fatalf("用法: %s <input.csv> <output.mmdb>", os.Args[0])
	}
	inPath, outPath := os.Args[1], os.Args[2]

	writer, err := mmdbwriter.New(mmdbwriter.Options{
		DatabaseType:            "GeoLite2-City",
		IPVersion:               4,
		Languages:               []string{"zh-CN", "en"},
		IncludeReservedNetworks: true,
		Description: map[string]string{
			"en":    "ipgeo multi-source merged IP geolocation database",
			"zh-CN": "ipgeo 多源融合 IP 地理位置数据库",
		},
	})
	if err != nil {
		log.Fatalf("创建 writer 失败: %v", err)
	}

	f, err := os.Open(inPath)
	if err != nil {
		log.Fatalf("打开 CSV 失败: %v", err)
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // 允许列数波动，按表头对齐
	header, err := r.Read()
	if err != nil {
		log.Fatalf("读取表头失败: %v", err)
	}
	col := map[string]int{}
	for i, h := range header {
		col[h] = i
	}

	n, skipped := 0, 0
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Fatalf("CSV 解析错误(第 %d 行): %v", n+2, err)
		}
		get := func(k string) string {
			if i, ok := col[k]; ok && i < len(row) {
				return row[i]
			}
			return ""
		}
		prefix, err := netip.ParsePrefix(get("network"))
		if err != nil {
			skipped++
			continue
		}
		conf, _ := strconv.ParseUint(get("confidence"), 10, 16)
		record := buildRecord(
			get("country"), get("province"), get("city"), get("isp"),
			get("asn"), get("network_type"), conf,
		)
		if err := writer.Insert(prefix, record); err != nil {
			// 保留段等个别插入失败可容忍，与 Python 版跳过行为一致
			skipped++
			continue
		}
		n++
		if n%1000000 == 0 {
			fmt.Printf("  已插入 %d 段...\n", n)
		}
	}
	fmt.Printf("插入完成: %d 段（跳过 %d 段）\n", n, skipped)

	out, err := os.Create(outPath)
	if err != nil {
		log.Fatalf("创建输出文件失败: %v", err)
	}
	defer out.Close()
	if _, err := writer.WriteTo(out); err != nil {
		log.Fatalf("写出 mmdb 失败: %v", err)
	}
	fmt.Printf("mmdb 已生成: %s\n", outPath)
}

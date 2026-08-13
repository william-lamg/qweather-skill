# 和风天气 (QWeather) API 参考

## 1. 认证方式
和风天气支持两种身份认证，推荐 JWT（安全性更高）：

### JWT（EdDSA / Ed25519 签名）
- 算法：`EdDSA`（底层 Ed25519，非 RSA）
- Header：`{"alg":"EdDSA","kid":"<凭据ID>"}`
- Payload：`{"sub":"<项目ID>","iat":now-30,"exp":iat+900}`
  - `sub` = 项目 ID（控制台-项目管理查看）
  - `kid` = 凭据 ID（添加凭据后查看）
  - `iat` 建议设为当前时间前 30 秒，防时间误差
  - `exp` 有效期最长 24 小时，示例用 15 分钟
- 用私钥对 `base64url(header).base64url(payload)` 签名，再 base64url 编码拼接：`header.payload.signature`
- 请求头：`Authorization: Bearer <JWT>`
- 公钥需上传控制台（私钥在本地生成，妥善保管，切勿提交仓库）

### API Key
- 请求头：`X-QW-Api-Key: <key>` 或 查询参数 `?key=<key>`
- 操作简单，适合测试；SDK 5+ 不再支持，2027-01-01 起限制每日用量

## 2. 基础 URL 与 Host
- URL 格式：`https://{host}/{version}/{endpoint}?location=...`
- **免费开发版**：天气与 GeoAPI **统一** `https://devapi.qweather.com`（GeoAPI 路径为 `devapi.qweather.com/geo/v2/...`）。注意：旧文档提到的专用 host `geoapi.qweather.com` 实测已弃用（返回 404），勿再用。
- **商业版**：统一 `https://<your-host>.qweatherapi.com`，GeoAPI 合并为 `<host>/geo/v2/...`
- 自己的 host 在控制台「设置」查看

## 3. location 参数
- LocationID（如 `101010100`）或 `经度,纬度`（如 `116.41,39.92`）
- 经纬度十进制，小数点后最多 2 位；逗号需 URL 编码为 `%2C`
- 建议先用 GeoAPI 城市搜索拿到 LocationID，更稳定

## 4. 端点速查表（脚本全量覆盖）

> 脚本 `scripts/qweather.py` 以「端点注册表」统一派发，以下命令名即子命令。
> `location` 既可为 LocationID（`101010100`）也可为 `经度,纬度`（`116.41,39.92`）。
> 标注「自动解析经纬度」的端点会把 LocationID/城市名经 GeoAPI 转成经纬度（部分新版端点强制要求经纬度路径参数）。

### 4.1 GeoAPI（城市 / 热门 / POI）— host: `/geo/v2/...`
| 命令 | 路径 | 参数 | 说明 |
|------|------|------|------|
| `lookup` | `/geo/v2/city/lookup` | location, adm, range, number(1-20), lang | 城市搜索，返回 LocationID、lat/lon |
| `top` | `/geo/v2/city/top` | location(可选), number(1-20), lang | 热门城市列表 |
| `poi` | `/geo/v2/poi/lookup` | location(`经度,纬度` 建议), type, number, lang | POI 搜索（scenic/cul/gov/edu/hosp/bus/cbd/ntour/tower） |
| `poi-range` | `/geo/v2/poi/range` | location(`经度,纬度`), type, radius(km), number, lang | POI 范围搜索 |

### 4.2 天气 — host: `/v7/weather/...` 等
| 命令 | 路径 | 参数 | 说明 |
|------|------|------|------|
| `now` | `/v7/weather/now` | location, lang | 实时天气 |
| `hourly` | `/v7/weather/{24h\|72h\|168h}` | location, hours(24/72/168), lang | 逐小时预报 |
| `daily` | `/v7/weather/{3d\|7d\|15d\|30d}` | location, days(3/7/15/30), lang | 每日预报 |
| `minutely` | `/v7/minutely/5m` | location(自动解析经纬度), lang | 分钟级降水（邻近预报，中国 1km） |
| `warning` | `/weatheralert/v1/current/{lat}/{lon}` | location(自动解析经纬度), lang | **实时天气预警（新版 v1）**，旧 `/v7/warning/now` 已弃用 |
| `indices` | `/v7/indices/{1d\|3d}` | location, type(如 `1,3,9`, `0`=全部), period(1d/3d), lang | 生活指数 |

### 4.3 空气质量（新版 airquality v1）— host: `/airquality/v1/...`
| 命令 | 路径 | 参数 | 说明 |
|------|------|------|------|
| `air` | `/airquality/v1/current/{lat}/{lon}` | location(自动解析经纬度), lang | 空气质量实况（AQI + 污染物） |
| `air-hourly` | `/airquality/v1/hourly/{lat}/{lon}` | location(自动解析经纬度), lang | 空气质量逐小时（未来 24h） |
| `air-daily` | `/airquality/v1/daily/{lat}/{lon}` | location(自动解析经纬度), lang | 空气质量每日（未来 3 天） |

> 旧版 `/v7/air/*` 已对新注册开发者弃用（403 DEPRECATED），一律改用上面 v1 路径。

### 4.4 天文 — host: `/v7/astronomy/...`
| 命令 | 路径 | 参数 | 说明 |
|------|------|------|------|
| `astro-sun` | `/v7/astronomy/sun` | location, date(yyyyMMdd), lang | 日出日落（未来 60 天） |
| `astro-moon` | `/v7/astronomy/moon` | location, date(yyyyMMdd), lang | 月升月落 + 月相 |
| `astro-solar` | `/v7/astronomy/solar-elevation-angle` | location(自动解析经纬度), date, time(HHmm), **tz(HHmm, 如 `0800`)**, alt(米), lang | 太阳高度角/方位角。**tz 必须 HHmm 格式（`0800`），非 `+08:00`**，否则 400 |

### 4.5 历史时光机 — host: `/v7/historical/...`
| 命令 | 路径 | 参数 | 说明 |
|------|------|------|------|
| `historical` | `/v7/historical/weather` | location, date(yyyyMMdd, 最近 10 天不含今天), unit(m/i), lang | 历史天气再分析 |
| `historical-air` | `/v7/historical/air` | location, date, unit(m/i), lang | 历史空气质量 |

### 4.6 太阳辐射 — host: `/solarradiation/v1/forecast/{lat}/{lon}`
| 命令 | 路径 | 参数 | 说明 |
|------|------|------|------|
| `solar` | `/solarradiation/v1/forecast/{lat}/{lon}` | location(自动解析经纬度), lang | 太阳辐射预报。**需订阅 Solar Radiation 产品，未订阅返回 403** |

### 4.7 台风（热带气旋）— host: `/v7/tropical/...`
| 命令 | 路径 | 参数 | 说明 |
|------|------|------|------|
| `tropical-list` | `/v7/tropical/storm-list` | basin(NP 西北太平洋, 目前唯一支持), year(今年/去年), lang | 台风列表（近 2 年） |
| `tropical-track` | `/v7/tropical/storm-track` | stormid(来自列表), lang | 台风实况与历史路径 |
| `tropical-forecast` | `/v7/tropical/storm-forecast` | stormid, lang | 台风预报路径 |

### 4.8 海洋 — host: `/v7/ocean/...`
| 命令 | 路径 | 参数 | 说明 |
|------|------|------|------|
| `tide` | `/v7/ocean/tide` | location(潮汐站 LocationID，用 `poi` 搜 `tower`/港口获取), date(yyyyMMdd, 未来 10 天), lang | 潮汐表（tideTable + tideHourly） |

### 4.9 关于响应顶层 `code`
- 大部分端点（GeoAPI、天气 v7、天文、历史、台风、海洋）响应含顶层 `"code":"200"`。
- **新版 `weatheralert/v1` 与 `airquality/v1` 无顶层 `code` 字段**，成功时直接返回 `metadata` + 数据（`alerts` / `indexes` / `pollutants` / `hours` / `days`）。脚本的 `report()` 已做兼容：仅当 `code is not None 且 != "200"` 才提示，故这两种端点不会误报失败。

## 5. 实时天气响应字段（now 对象）
| 字段 | 含义 |
|------|------|
| obsTime | 观测时间 |
| temp | 温度（℃） |
| feelsLike | 体感温度 |
| icon | 天气图标代码 |
| text | 天气文字描述 |
| wind360 | 风向 360 角度 |
| windDir | 风向 |
| windScale | 风力等级 |
| windSpeed | 风速（km/h） |
| humidity | 相对湿度（%） |
| precip | 降水量（mm） |
| pressure | 气压（hPa） |
| vis | 能见度（km） |
| cloud | 云量（%） |
| dew | 露点温度 |

顶层字段：`code`、`updateTime`、`fxLink`、`refer`。

## 6. 城市搜索响应（location[] 数组）
每个元素：`id`(LocationID)、`name`、`lat`、`lon`、`adm1`(省)、`adm2`(市)、`country`、`tz`(时区)、`type`、`rank`、`fxLink`。
注意：`fxLink` 常拼写为返回字段名；部分版本为 `fxLink`。

## 7. 错误码（响应 code 字段 / HTTP 状态）
| code | HTTP | 含义与处理 |
|------|------|-----------|
| 200 | 200 | 成功 |
| 204 | 200 | 成功但无数据（地点不支持该数据） |
| — | 400 | 参数错误 / 缺失 / 无此地点 / 数据不可用 |
| 401 | 401 | 认证失败：检查 Key 或 JWT（kid/sub/私钥） |
| 403 | 403 | 无额度(NO CREDIT)/逾期(OVERDUE)/Host错(INVALID HOST)/权限(FORBIDDEN)/弃用(DEPRECATED) |
| 404 | 404 | 路径或路径参数错误 |
| 429 | 429 | 请求过多：降频 + 指数退避，否则可能冻结账号 |
| 5xx | 500+ | 服务端故障，提交工单 |

## 8. 最佳实践
- 请求加 `Accept-Encoding: gzip`（脚本已处理），用 `--compressed`
- **错误请求持续发送会被安全策略视为 DDoS，可能冻结账号**：遇错先停排查
- 缓存数据、对 429 使用指数退避重试
- 不要在 Header/Payload 放敏感信息（明文传输）
- 付费版请勿混用免费版 host

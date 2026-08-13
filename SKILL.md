---
name: qweather
description: 调用和风天气 (QWeather) API 查询天气、空气质量、生活指数与城市搜索。当用户需要查询实时天气、天气预报、空气质量、生活指数，或使用和风天气 API（JWT/API Key 认证、GeoAPI 城市搜索、LocationID 解析）时使用此 skill。触发词包括「和风天气」「QWeather」「天气查询」「空气质量」「城市搜索」「LocationID」。
agent_created: true
---

# QWeather (和风天气) API Skill

## Overview
封装和风天气开发者 API 的**全部分类**：城市搜索 / 热门城市 / POI（GeoAPI）、实时天气 / 逐小时 / 每日 / 分钟级 / 预警 / 生活指数、空气质量（新版 airquality v1 实况/逐时/每日）、天文（日出日落 / 月升月落 / 太阳高度角）、历史时光机（天气 / 空气质量）、太阳辐射、台风（列表 / 路径 / 预报）、海洋潮汐。支持 JWT（Ed25519/EdDSA 签名）与 API Key 两种认证，脚本仅依赖标准库 + `cryptography`，以「端点注册表」统一派发 22 个子命令。

## When to use
- 查询某城市或坐标的实时天气、逐小时/每日预报、空气质量、生活指数
- 通过城市名解析 LocationID（再用于天气查询）
- 配置或调试和风天气认证（JWT 私钥签名、API Key、host 设置）
- 排查 QWeather 错误码、host 不匹配、限流等问题

## Quick Start
1. 安装依赖：`pip install cryptography`（JWT 签名必需；API Key 模式可不装）。
2. 获取凭据：到和风天气开发服务平台 https://dev.qweather.com/ 注册后，控制台 → 项目管理 → 添加凭据（JSON Web Token 或 API Key），拿到：
   - 天气 host（免费版 `devapi.qweather.com`；商业版 `your-xxx.qweatherapi.com`）
   - JWT：`kid`(凭据ID)、`sub`(项目ID)、私钥 PEM；或 API Key
3. 工作流：先用 `lookup` 拿 LocationID，再用其查天气。

## Commands
调用 `scripts/qweather.py`。通用参数：
`--host <host>`（天气 host，默认 `devapi.qweather.com`）
`--auth jwt|apikey`（默认 apikey）
JWT 模式：`--key-path <私钥.pem> --kid <凭据ID> --sub <项目ID>`
API Key 模式：`--apikey <key>`
`--raw` 输出未格式化 JSON；`--print-token` 仅打印 JWT（调试，不请求）

示例：
```bash
# API Key 模式
python scripts/qweather.py --auth apikey --apikey $QW_KEY lookup 北京
python scripts/qweather.py --auth apikey --apikey $QW_KEY now 101010100
python scripts/qweather.py --auth apikey --apikey $QW_KEY daily 116.41,39.92 --days 15
python scripts/qweather.py --auth apikey --apikey $QW_KEY air 101010100        # 新 airquality v1
python scripts/qweather.py --auth apikey --apikey $QW_KEY warning 101010100     # 新 weatheralert v1
python scripts/qweather.py --auth apikey --apikey $QW_KEY indices 101010100 --type 1,3,9
python scripts/qweather.py --auth apikey --apikey $QW_KEY astro-solar 101010100 # tz 默认 0800
python scripts/qweather.py --auth apikey --apikey $QW_KEY tropical-list --basin NP --year 2026
python scripts/qweather.py --auth apikey --apikey $QW_KEY tide P2951 --date 20260814

# JWT 模式（用你下载的私钥 PEM）
python scripts/qweather.py --auth jwt --key-path /path/to/ed25519-private.pem \
  --kid <凭据ID> --sub <项目ID> now 北京
```

详细端点路径、参数、响应字段、错误码见 `references/api.md`。

## 端点速查（22 个子命令）
| 命令 | 路径 | 说明 |
|------|------|------|
| `lookup` | `/geo/v2/city/lookup` | 城市搜索，返回 LocationID |
| `top` | `/geo/v2/city/top` | 热门城市列表 |
| `poi` | `/geo/v2/poi/lookup` | POI 搜索（建议用 经度,纬度） |
| `poi-range` | `/geo/v2/poi/range` | POI 范围搜索 |
| `now` | `/v7/weather/now` | 实时天气 |
| `hourly` | `/v7/weather/{24h,72h,168h}` | 逐小时预报 |
| `daily` | `/v7/weather/{3d,7d,15d,30d}` | 每日预报 |
| `minutely` | `/v7/minutely/5m` | 分钟级降水（自动解析经纬度） |
| `warning` | `/weatheralert/v1/current/{lat}/{lon}` | 实时预警（新版 v1） |
| `indices` | `/v7/indices/{1d,3d}` | 生活指数 |
| `air` | `/airquality/v1/current/{lat}/{lon}` | 空气质量实况（新版 v1） |
| `air-hourly` | `/airquality/v1/hourly/{lat}/{lon}` | 空气质量逐小时 |
| `air-daily` | `/airquality/v1/daily/{lat}/{lon}` | 空气质量每日 |
| `astro-sun` | `/v7/astronomy/sun` | 日出日落 |
| `astro-moon` | `/v7/astronomy/moon` | 月升月落 / 月相 |
| `astro-solar` | `/v7/astronomy/solar-elevation-angle` | 太阳高度角（tz 用 0800） |
| `historical` | `/v7/historical/weather` | 历史天气时光机 |
| `historical-air` | `/v7/historical/air` | 历史空气质量时光机 |
| `solar` | `/solarradiation/v1/forecast/{lat}/{lon}` | 太阳辐射（需订阅，否则 403） |
| `tropical-list` | `/v7/tropical/storm-list` | 台风列表 |
| `tropical-track` | `/v7/tropical/storm-track` | 台风实况与路径 |
| `tropical-forecast` | `/v7/tropical/storm-forecast` | 台风预报路径 |
| `tide` | `/v7/ocean/tide` | 潮汐（需潮汐站 LocationID） |

## 注意事项
- `location` 可为 LocationID 或 `经度,纬度`（逗号需 URL 编码 `%2C`）
- **免费版与商业版的 GeoAPI 均已合并进主 host**（`devapi.qweather.com` / `your-xxx.qweatherapi.com`），旧的专用 host `geoapi.qweather.com` 已弃用（404），勿再用
- `warning` / `air*` / `minutely` / `solar` 等强制要求经纬度的端点，脚本会自动把 LocationID/城市名经 GeoAPI 转成经纬度
- `astro-solar` 的 `tz` 参数必须是 `HHmm` 格式（如 `0800`），不是 `+08:00`
- 遇 `401` 检查认证；`429` 限流需退避重试；`404` 检查 host/路径版本
- 错误请求持续发送会被视为 DDoS，可能冻结账号，遇错先停排查
- 私钥等同账号身份，仅本地保管，切勿外泄或提交到仓库

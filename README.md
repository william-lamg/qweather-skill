# QWeather (和风天气) API Skill

**[简体中文](README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md)**

一个封装[和风天气开发者 API](https://dev.qweather.com/)全部主要分类的命令行工具 / Agent Skill，基于「端点注册表」统一派发 **22 个子命令**，覆盖：

- **GeoAPI**：城市搜索（LocationID）、热门城市、POI 搜索 / 范围搜索
- **天气 v7**：实时、逐小时（24/72/168h）、每日（3/7/15/30d）、分钟级降水、天气预警、生活指数
- **空气质量 airquality v1**：实况 / 逐小时 / 每日（新版接口）
- **天文**：日出日落、月升月落 / 月相、太阳高度角
- **历史时光机**：历史天气、历史空气质量
- **太阳辐射 / 台风 / 海洋**：太阳辐射预报、台风列表 / 路径 / 预报、潮汐

支持 **JWT（EdDSA / Ed25519 签名）** 与 **API Key** 两种认证方式，脚本仅依赖 Python 标准库 + `cryptography`（无第三方 HTTP 库）。

## 如何获取 API Key

和风天气 API 需要先在官网注册开发者账号，再创建项目并添加凭据：

1. 打开和风天气开发服务平台：**https://dev.qweather.com/**
2. 注册 / 登录账号（免费注册，免费版自带每日请求额度）
3. 进入**控制台 → 项目管理**，点击「创建项目」
4. 在项目详情页点击「**添加凭据**」，选择凭据类型：
   - **API Key**：直接生成一串 Key（适合快速测试）
   - **JSON Web Token**：生成后你会拿到「凭据 ID」和「项目 ID」，并**下载私钥 PEM 文件（仅下载一次）**
5. 在控制台「**设置**」页面查看你的专属 **Host**：
   - 免费版：`devapi.qweather.com`
   - 商业版：`<your-xxx>.qweatherapi.com`（订阅后分配）

拿到后对应到脚本参数：

| 认证方式 | 需要的参数 |
|----------|-----------|
| API Key | `--auth apikey --apikey <你的Key>` |
| JWT | `--auth jwt --key-path <私钥.pem> --kid <凭据ID> --sub <项目ID>` |

> ⚠️ **安全提醒**：API Key 和私钥等同你的账号身份，**切勿提交到代码仓库**。建议通过环境变量（如 `QW_API_KEY`）或本地的 `.gitignore` 管理。

## 快速开始

```bash
# 1. 安装依赖（JWT 签名需要；API Key 模式可省略）
pip install cryptography

# 2. 查询城市（先拿 LocationID，例如北京 101010100）
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY lookup 北京

# 3. 查询天气（支持 LocationID、城市名或 "经度,纬度"）
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY now 101010100
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY daily 116.41,39.92 --days 15
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY air 101010100
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY indices 101010100 --type 1,3,9
```

JWT 模式示例：

```bash
python scripts/qweather.py --auth jwt \
  --key-path /path/to/ed25519-private.pem \
  --kid <凭据ID> --sub <项目ID> \
  --host devapi.qweather.com now 北京
```

常用通用参数：

- `--host <host>`：天气 host，默认 `devapi.qweather.com`
- `--raw`：输出原始 JSON（不格式化）
- `--print-token`：仅打印 JWT（调试用，不发请求）

## 端点速查（22 个子命令）

| 命令 | 路径 | 说明 |
|------|------|------|
| `lookup` | `/geo/v2/city/lookup` | 城市搜索，返回 LocationID |
| `top` | `/geo/v2/city/top` | 热门城市列表 |
| `poi` | `/geo/v2/poi/lookup` | POI 搜索（建议用 `经度,纬度`） |
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
| `astro-solar` | `/v7/astronomy/solar-elevation-angle` | 太阳高度角（`tz` 用 `0800` 格式） |
| `historical` | `/v7/historical/weather` | 历史天气时光机（需订阅） |
| `historical-air` | `/v7/historical/air` | 历史空气质量时光机（需订阅） |
| `solar` | `/solarradiation/v1/forecast/{lat}/{lon}` | 太阳辐射（需订阅，否则 403） |
| `tropical-list` | `/v7/tropical/storm-list` | 台风列表 |
| `tropical-track` | `/v7/tropical/storm-track` | 台风实况与路径 |
| `tropical-forecast` | `/v7/tropical/storm-forecast` | 台风预报路径 |
| `tide` | `/v7/ocean/tide` | 潮汐（需潮汐站 LocationID） |

> 详细端点参数、响应字段、错误码见 [`references/api.md`](references/api.md)。

## 注意事项

- `location` 可为 LocationID 或 `经度,纬度`（逗号需 URL 编码 `%2C`）
- **GeoAPI 已并入主 host**：免费版 `devapi.qweather.com`，商业版 `<your-xxx>.qweatherapi.com`；旧专用 host `geoapi.qweather.com` 已弃用（404）
- `warning` / `air*` / `minutely` / `solar` 等强制经纬度的端点，脚本会自动把 LocationID / 城市名经 GeoAPI 转成经纬度
- `astro-solar` 的 `tz` 参数必须是 `HHmm` 格式（如 `0800`），不是 `+08:00`
- 遇 `401` 检查认证；`429` 限流需退避重试；`404` 检查 host / 路径版本
- 部分付费产品（历史天气、太阳辐射等）需要订阅，未订阅会返回 `403`
- 错误请求持续发送会被视为 DDoS，可能冻结账号，遇错先停排查

## 安装为 Agent Skill（可选）

本项目同时可作为 WorkBuddy / Agent Skill 使用。将本仓库放入 `~/.workbuddy/skills/` 目录（或项目 `.workbuddy/skills/`），AI 助手即可通过 `SKILL.md` 的元数据自动识别并调用。

## License

MIT

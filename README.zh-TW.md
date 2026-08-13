# QWeather (和風天氣) API Skill

**[简体中文](README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md)**

一個封裝[和風天氣開發者 API](https://dev.qweather.com/)全部主要分類的命令列工具 / Agent Skill，基於「端點註冊表」統一派發 **22 個子命令**，涵蓋：

- **GeoAPI**：城市搜尋（LocationID）、熱門城市、POI 搜尋 / 範圍搜尋
- **天氣 v7**：即時、逐小時（24/72/168h）、每日（3/7/15/30d）、分鐘級降水、天氣預警、生活指數
- **空氣品質 airquality v1**：實況 / 逐小時 / 每日（新版介面）
- **天文**：日出日落、月升月落 / 月相、太陽高度角
- **歷史時光機**：歷史天氣、歷史空氣品質
- **太陽輻射 / 颱風 / 海洋**：太陽輻射預報、颱風列表 / 路徑 / 預報、潮汐

支援 **JWT（EdDSA / Ed25519 簽名）** 與 **API Key** 兩種認證方式，腳本僅依賴 Python 標準庫 + `cryptography`（無第三方 HTTP 函式庫）。

## 如何取得 API Key

和風天氣 API 需要先在官網註冊開發者帳號，再建立專案並新增憑據：

1. 開啟和風天氣開發服務平台：**https://dev.qweather.com/**
2. 註冊 / 登入帳號（免費註冊，免費版自帶每日請求額度）
3. 進入**控制台 → 專案管理**，點擊「建立專案」
4. 在專案詳情頁點擊「**新增憑據**」，選擇憑據類型：
   - **API Key**：直接產生一串 Key（適合快速測試）
   - **JSON Web Token**：產生後你會拿到「憑據 ID」和「專案 ID」，並**下載私鑰 PEM 檔案（僅下載一次）**
5. 在控制台「**設定**」頁面查看你的專屬 **Host**：
   - 免費版：`devapi.qweather.com`
   - 商業版：`<your-xxx>.qweatherapi.com`（訂閱後分配）

拿到後對應到腳本參數：

| 認證方式 | 需要的參數 |
|----------|-----------|
| API Key | `--auth apikey --apikey <你的Key>` |
| JWT | `--auth jwt --key-path <私鑰.pem> --kid <憑據ID> --sub <專案ID>` |

> ⚠️ **安全提醒**：API Key 和私鑰等同你的帳號身分，**切勿提交到程式碼倉庫**。建議透過環境變數（如 `QW_API_KEY`）或本地的 `.gitignore` 管理。

## 快速開始

```bash
# 1. 安裝依賴（JWT 簽名需要；API Key 模式可省略）
pip install cryptography

# 2. 查詢城市（先拿 LocationID，例如北京 101010100）
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY lookup 北京

# 3. 查詢天氣（支援 LocationID、城市名或 "經度,緯度"）
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY now 101010100
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY daily 116.41,39.92 --days 15
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY air 101010100
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY indices 101010100 --type 1,3,9
```

JWT 模式範例：

```bash
python scripts/qweather.py --auth jwt \
  --key-path /path/to/ed25519-private.pem \
  --kid <憑據ID> --sub <專案ID> \
  --host devapi.qweather.com now 北京
```

常用通用參數：

- `--host <host>`：天氣 host，預設 `devapi.qweather.com`
- `--raw`：輸出原始 JSON（不格式化）
- `--print-token`：僅列印 JWT（除錯用，不發請求）

## 端點速查（22 個子命令）

| 命令 | 路徑 | 說明 |
|------|------|------|
| `lookup` | `/geo/v2/city/lookup` | 城市搜尋，回傳 LocationID |
| `top` | `/geo/v2/city/top` | 熱門城市列表 |
| `poi` | `/geo/v2/poi/lookup` | POI 搜尋（建議用 `經度,緯度`） |
| `poi-range` | `/geo/v2/poi/range` | POI 範圍搜尋 |
| `now` | `/v7/weather/now` | 即時天氣 |
| `hourly` | `/v7/weather/{24h,72h,168h}` | 逐小時預報 |
| `daily` | `/v7/weather/{3d,7d,15d,30d}` | 每日預報 |
| `minutely` | `/v7/minutely/5m` | 分鐘級降水（自動解析經緯度） |
| `warning` | `/weatheralert/v1/current/{lat}/{lon}` | 即時預警（新版 v1） |
| `indices` | `/v7/indices/{1d,3d}` | 生活指數 |
| `air` | `/airquality/v1/current/{lat}/{lon}` | 空氣品質實況（新版 v1） |
| `air-hourly` | `/airquality/v1/hourly/{lat}/{lon}` | 空氣品質逐小時 |
| `air-daily` | `/airquality/v1/daily/{lat}/{lon}` | 空氣品質每日 |
| `astro-sun` | `/v7/astronomy/sun` | 日出日落 |
| `astro-moon` | `/v7/astronomy/moon` | 月升月落 / 月相 |
| `astro-solar` | `/v7/astronomy/solar-elevation-angle` | 太陽高度角（`tz` 用 `0800` 格式） |
| `historical` | `/v7/historical/weather` | 歷史天氣時光機（需訂閱） |
| `historical-air` | `/v7/historical/air` | 歷史空氣品質時光機（需訂閱） |
| `solar` | `/solarradiation/v1/forecast/{lat}/{lon}` | 太陽輻射（需訂閱，否則 403） |
| `tropical-list` | `/v7/tropical/storm-list` | 颱風列表 |
| `tropical-track` | `/v7/tropical/storm-track` | 颱風實況與路徑 |
| `tropical-forecast` | `/v7/tropical/storm-forecast` | 颱風預報路徑 |
| `tide` | `/v7/ocean/tide` | 潮汐（需潮汐站 LocationID） |

> 詳細端點參數、回應欄位、錯誤碼見 [`references/api.md`](references/api.md)。

## 注意事項

- `location` 可為 LocationID 或 `經度,緯度`（逗號需 URL 編碼 `%2C`）
- **GeoAPI 已併入主 host**：免費版 `devapi.qweather.com`，商業版 `<your-xxx>.qweatherapi.com`；舊專用 host `geoapi.qweather.com` 已棄用（404）
- `warning` / `air*` / `minutely` / `solar` 等強制經緯度的端點，腳本會自動把 LocationID / 城市名經 GeoAPI 轉成經緯度
- `astro-solar` 的 `tz` 參數必須是 `HHmm` 格式（如 `0800`），不是 `+08:00`
- 遇 `401` 檢查認證；`429` 限流需退避重試；`404` 檢查 host / 路徑版本
- 部分付費產品（歷史天氣、太陽輻射等）需要訂閱，未訂閱會回傳 `403`
- 錯誤請求持續發送會被視為 DDoS，可能凍結帳號，遇錯先停排查

## 安裝為 Agent Skill（可選）

本專案同時可作為 WorkBuddy / Agent Skill 使用。將本倉庫放入 `~/.workbuddy/skills/` 目錄（或專案 `.workbuddy/skills/`），AI 助手即可透過 `SKILL.md` 的中繼資料自動識別並呼叫。

## License

MIT

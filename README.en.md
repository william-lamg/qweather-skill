# QWeather API Skill

**Language: [简体中文](README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md)**

A command-line tool / Agent Skill that wraps all major categories of the [QWeather Developer API](https://dev.qweather.com/), dispatching **22 subcommands** from a unified "endpoint registry":

- **GeoAPI**: city lookup (LocationID), top cities, POI lookup / range search
- **Weather v7**: real-time, hourly (24/72/168h), daily (3/7/15/30d), minutely precipitation, weather alerts, life indices
- **Air quality airquality v1**: current / hourly / daily (new API)
- **Astronomy**: sunrise/sunset, moonrise/moonset & moon phase, solar elevation angle
- **History**: historical weather, historical air quality
- **Solar radiation / Tropical cyclone / Ocean**: solar radiation forecast, storm list / track / forecast, tide

Supports both **JWT (EdDSA / Ed25519 signing)** and **API Key** authentication. The script only depends on the Python standard library + `cryptography` (no third-party HTTP library).

## Getting an API Key

You need to register a developer account on the QWeather website, then create a project and add credentials:

1. Open the QWeather Developer Platform: **https://dev.qweather.com/**
2. Register / sign in (free; the free tier includes a daily request quota)
3. Go to **Console → Project Management** and click "Create Project"
4. On the project page click "**Add Credential**" and choose a type:
   - **API Key**: generates a key string directly (great for quick testing)
   - **JSON Web Token**: you'll get a "Credential ID" and "Project ID", and **download a private key PEM file (only downloadable once)**
5. Find your dedicated **Host** on the Console "**Settings**" page:
   - Free tier: `devapi.qweather.com`
   - Commercial: `<your-xxx>.qweatherapi.com` (assigned after subscription)

Map them to the script arguments:

| Auth | Required arguments |
|------|--------------------|
| API Key | `--auth apikey --apikey <your-key>` |
| JWT | `--auth jwt --key-path <private-key.pem> --kid <credential-id> --sub <project-id>` |

> ⚠️ **Security**: your API Key / private key is your account identity — **never commit it to a repository**. Prefer environment variables (e.g. `QW_API_KEY`) or a local `.gitignore`.

## Quick Start

```bash
# 1. Install dependencies (needed for JWT signing; optional for API Key mode)
pip install cryptography

# 2. Look up a city (get a LocationID, e.g. Beijing 101010100)
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY lookup 北京

# 3. Query weather (accepts LocationID, city name, or "longitude,latitude")
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY now 101010100
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY daily 116.41,39.92 --days 15
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY air 101010100
python scripts/qweather.py --auth apikey --apikey $QW_API_KEY indices 101010100 --type 1,3,9
```

JWT mode example:

```bash
python scripts/qweather.py --auth jwt \
  --key-path /path/to/ed25519-private.pem \
  --kid <credential-id> --sub <project-id> \
  --host devapi.qweather.com now 北京
```

Common global arguments:

- `--host <host>`: weather host, default `devapi.qweather.com`
- `--raw`: print raw JSON (no formatting)
- `--print-token`: print the JWT only (debugging, no request)

## Endpoint Reference (22 subcommands)

| Command | Path | Description |
|---------|------|-------------|
| `lookup` | `/geo/v2/city/lookup` | City lookup, returns LocationID |
| `top` | `/geo/v2/city/top` | Top cities |
| `poi` | `/geo/v2/poi/lookup` | POI lookup (prefer `longitude,latitude`) |
| `poi-range` | `/geo/v2/poi/range` | POI range search |
| `now` | `/v7/weather/now` | Real-time weather |
| `hourly` | `/v7/weather/{24h,72h,168h}` | Hourly forecast |
| `daily` | `/v7/weather/{3d,7d,15d,30d}` | Daily forecast |
| `minutely` | `/v7/minutely/5m` | Minutely precipitation (auto-resolves lat/lon) |
| `warning` | `/weatheralert/v1/current/{lat}/{lon}` | Real-time alerts (new v1) |
| `indices` | `/v7/indices/{1d,3d}` | Life indices |
| `air` | `/airquality/v1/current/{lat}/{lon}` | Air quality current (new v1) |
| `air-hourly` | `/airquality/v1/hourly/{lat}/{lon}` | Air quality hourly |
| `air-daily` | `/airquality/v1/daily/{lat}/{lon}` | Air quality daily |
| `astro-sun` | `/v7/astronomy/sun` | Sunrise / sunset |
| `astro-moon` | `/v7/astronomy/moon` | Moonrise / moonset & phase |
| `astro-solar` | `/v7/astronomy/solar-elevation-angle` | Solar elevation angle (`tz` in `0800` format) |
| `historical` | `/v7/historical/weather` | Historical weather (subscription required) |
| `historical-air` | `/v7/historical/air` | Historical air quality (subscription required) |
| `solar` | `/solarradiation/v1/forecast/{lat}/{lon}` | Solar radiation (subscription required, else 403) |
| `tropical-list` | `/v7/tropical/storm-list` | Storm list |
| `tropical-track` | `/v7/tropical/storm-track` | Storm track |
| `tropical-forecast` | `/v7/tropical/storm-forecast` | Storm forecast track |
| `tide` | `/v7/ocean/tide` | Tide (needs a tide-station LocationID) |

> Detailed endpoint params, response fields and error codes: see [`references/api.md`](references/api.md).

## Notes

- `location` can be a LocationID or `longitude,latitude` (the comma must be URL-encoded as `%2C`)
- **GeoAPI is merged into the main host**: free `devapi.qweather.com`, commercial `<your-xxx>.qweatherapi.com`; the legacy dedicated host `geoapi.qweather.com` is deprecated (404)
- Endpoints that require lat/lon (`warning`, `air*`, `minutely`, `solar`, etc.) auto-resolve LocationID / city names to coordinates via GeoAPI
- `astro-solar` requires `tz` in `HHmm` format (e.g. `0800`), not `+08:00`
- `401` = check authentication; `429` = rate-limited, back off and retry; `404` = check host / API version
- Some paid products (historical weather, solar radiation, etc.) require a subscription; without it you'll get `403`
- Continuously sending bad requests may be treated as DDoS and could freeze your account — stop and debug on errors

## Install as an Agent Skill (optional)

This project can also be used as a WorkBuddy / Agent Skill. Put this repository under `~/.workbuddy/skills/` (or a project's `.workbuddy/skills/`), and AI assistants will auto-detect and invoke it via the `SKILL.md` metadata.

## License

MIT

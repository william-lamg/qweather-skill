#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QWeather (和风天气) API client.

支持两种认证方式（JWT / Ed25519 签名、API Key）以及和风天气 API 的全部分类：
GeoAPI（城市/热门/POI）、天气（实况/逐小时/每日/分钟级/预警/指数）、
空气质量（实况/逐时/每日，新版 airquality v1）、天文（日出日落/月升月落/太阳高度角）、
历史时光机、太阳辐射、台风（列表/路径/预报）、海洋（潮汐）。

仅依赖 Python 标准库 + cryptography（用于 JWT 签名）。

依赖：
    pip install cryptography

常用命令：
    # 城市搜索（返回 LocationID）
    qweather.py --auth apikey --apikey YOUR_KEY lookup 北京
    qweather.py --auth jwt --key-path ed25519-private.pem --kid KID --sub PID lookup 北京

    # 实时天气 / 逐小时 / 每日 / 分钟级 / 预警 / 指数
    qweather.py --auth apikey --apikey YOUR_KEY now 101010100
    qweather.py --auth apikey --apikey YOUR_KEY now 116.41,39.92
    qweather.py --auth apikey --apikey YOUR_KEY hourly 101010100 --hours 24
    qweather.py --auth apikey --apikey YOUR_KEY daily  101010100 --days 7
    qweather.py --auth apikey --apikey YOUR_KEY minutely 101010100
    qweather.py --auth apikey --apikey YOUR_KEY warning 101010100
    qweather.py --auth apikey --apikey YOUR_KEY indices 101010100 --type 1,3,9 --period 3d

    # 空气质量（新版 airquality v1，自动将 LocationID 解析为经纬度）
    qweather.py --auth apikey --apikey YOUR_KEY air 101010100
    qweather.py --auth apikey --apikey YOUR_KEY air-hourly 101010100
    qweather.py --auth apikey --apikey YOUR_KEY air-daily 101010100

    # 天文 / 历史 / 太阳 / 台风 / 海洋
    qweather.py --auth apikey --apikey YOUR_KEY astro-sun 101010100 --date 20260814
    qweather.py --auth apikey --apikey YOUR_KEY astro-solar 101010100
    qweather.py --auth apikey --apikey YOUR_KEY historical 101010100 --date 20260801
    qweather.py --auth apikey --apikey YOUR_KEY tropical-list --basin NP --year 2026
    qweather.py --auth apikey --apikey YOUR_KEY tide P2951 --date 20260814

说明：
    --host  天气 API host。免费版默认 devapi.qweather.com；商业版填 your-xxx.qweatherapi.com
    --geo-host  GeoAPI host。免费版已合并进主 host（自动）；商业版与主 host 合并
    location 既可以是 LocationID（如 101010100），也可以是 "经度,纬度"（如 116.41,39.92）
    需要经纬度的端点（minutely / warning / air* / solar 辐射）会自动将 LocationID 解析为经纬度
"""

import argparse
import base64
import datetime
import gzip
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

try:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
except ImportError:
    sys.stderr.write("ERROR: missing 'cryptography'. Run: pip install cryptography\n")
    sys.exit(2)


def b64url(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def make_jwt(key_path: str, kid: str, sub: str) -> str:
    """用 Ed25519 私钥生成 QWeather 要求的 JWT（alg=EdDSA）。"""
    with open(key_path, "rb") as f:
        key = load_pem_private_key(f.read(), password=None)
    header = {"alg": "EdDSA", "kid": kid}
    iat = int(time.time()) - 30  # 防时间误差，提前 30 秒
    exp = iat + 900             # 有效期 15 分钟
    payload = {"sub": sub, "iat": iat, "exp": exp}
    h = b64url(json.dumps(header, separators=(",", ":")).encode())
    p = b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = h + b"." + p
    sig = key.sign(signing_input)  # Ed25519 直接对原始字节签名
    return (signing_input + b"." + b64url(sig)).decode()


def geo_base_host(host: str, geo_host: str | None) -> str:
    """GeoAPI host 推断。

    实测：和风免费开发者版 GeoAPI 已合并进主 host (devapi.qweather.com)，
    旧的专用 host geoapi.qweather.com 的 /geo/v2/city/lookup 返回 404（已弃用）。
    因此默认 GeoAPI 与主 host 相同；仅当用户显式传入 --geo-host（如商业版
    拆分部署）时才覆盖。
    """
    if geo_host:
        return geo_host
    return host


def http_get(host: str, path: str, params: dict, auth_header: tuple) -> dict:
    """发起 GET 请求并返回解析后的 JSON。auth_header = ("X-QW-Api-Key", key) 或 ("Authorization", "Bearer ...")。"""
    url = "https://" + host + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Accept-Encoding", "gzip")
    req.add_header(*auth_header)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            text = raw.decode("utf-8")
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP {e.code}: {e.reason}\n")
        try:
            body = e.read()
            if e.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            sys.stderr.write(body.decode("utf-8", "replace") + "\n")
        except Exception:
            pass
        sys.exit(1)
    except urllib.error.URLError as e:
        sys.stderr.write(f"NETWORK ERROR: {e.reason}\n")
        sys.exit(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        sys.stderr.write("RESPONSE NOT JSON:\n" + text + "\n")
        sys.exit(1)


ERROR_HINTS = {
    "401": "认证失败：检查 API Key 或 JWT 的 kid/sub/私钥是否正确。",
    "403": "权限/额度/Host 错误：检查 API Host、订阅额度、是否触发请求限制。",
    "404": "路径错误：确认 endpoint 路径与 host 是否匹配版本。",
    "429": "请求过多：降低频率，使用指数退避重试，否则可能被冻结账号。",
    "204": "查询成功但无数据（如该地点不支持该数据）。",
}


def report(data: dict, raw: bool):
    if not raw:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False))
    code = data.get("code")
    if code is not None and str(code) != "200":
        hint = ERROR_HINTS.get(str(code), "")
        sys.stderr.write(f"\n[QWeather code {code}] {hint}\n")


def resolve_auth(args) -> tuple:
    if args.auth == "jwt":
        if not (args.key_path and args.kid and args.sub):
            sys.stderr.write("JWT 认证需提供 --key-path、--kid、--sub\n")
            sys.exit(2)
        token = make_jwt(args.key_path, args.kid, args.sub)
        return ("Authorization", "Bearer " + token)
    else:
        if not args.apikey:
            sys.stderr.write("API Key 认证需提供 --apikey\n")
            sys.exit(2)
        return ("X-QW-Api-Key", args.apikey)


COORD_RE = re.compile(r"^-?\d+(\.\d+)?,-?\d+(\.\d+)?$")


def resolve_latlon(location: str, auth_header: tuple, host: str):
    """将 LocationID / 城市名解析为 (lat, lon) 浮点元组。

    若输入已是 "经度,纬度" 坐标则直接解析；否则通过 GeoAPI 城市搜索取 lat/lon。
    用于 minutely / warning / air* / solarradiation 等必须用经纬度的端点。
    注意 QWeather 的 location 查询参数约定为 "经度,纬度"(lon,lat)，
    而 airquality/weatheralert 等路径参数为 /{latitude}/{longitude}(lat,lon)。
    """
    location = (location or "").strip()
    if COORD_RE.match(location):
        lon_s, lat_s = location.split(",")
        return float(lat_s), float(lon_s)
    data = http_get(geo_base_host(host, None), "/geo/v2/city/lookup",
                    {"location": location, "number": "1"}, auth_header)
    locs = data.get("location") or []
    if not locs:
        sys.stderr.write(f"无法将 location 解析为经纬度: {location}\n")
        sys.exit(1)
    return float(locs[0]["lat"]), float(locs[0]["lon"])


def resolve_location_to_param(location: str, auth_header: tuple, host: str) -> str:
    """将 LocationID / 城市名 / 坐标 统一解析为天气接口接受的 location 查询参数。

    QWeather 的天气/天文/历史等接口 location 只接受 LocationID 或 "经度,纬度"
    (lon,lat)，不接受中文城市名。故此处将非坐标输入经 GeoAPI 城市搜索转为
    "经度,纬度"。已是坐标则原样返回。
    """
    location = (location or "").strip()
    if COORD_RE.match(location):
        return location
    data = http_get(geo_base_host(host, None), "/geo/v2/city/lookup",
                    {"location": location, "number": "1"}, auth_header)
    locs = data.get("location") or []
    if not locs:
        sys.stderr.write(f"无法解析 location 为经纬度: {location}\n")
        sys.exit(1)
    return "%.2f,%.2f" % (float(locs[0]["lon"]), float(locs[0]["lat"]))


# ---------------------------------------------------------------------------
# 端点注册表
# 每个端点:
#   host: "main" 天气/空气/天文等主 host；"geo" GeoAPI（城市/POI）
#   path: 请求路径模板，{var} 会被同名参数替换（路径变量）
#   pos:  位置参数名列表（同时作为查询参数名）
#   opts: 可选参数列表，每项 (name, required, default, choices, help)
#   latlon_path: True 表示将 pos[0] 解析为经纬度并填入路径 {lat}/{lon}
#   resolve_latlon: True 表示将 pos[0] 解析为 "lat,lon" 作为 location 查询参数
#
# 注意：依据和风官方 OpenAPI（qweather-apis），旧版 /v7/warning/now 与
# /v7/air/* 已对新注册开发者弃用（403），故 warning 用 /weatheralert/v1/current，
# 空气质量用 /airquality/v1/*（均需经纬度）。
# ---------------------------------------------------------------------------
ENDPOINTS = [
    # ---- GeoAPI ----
    {"name": "lookup", "host": "geo", "path": "/geo/v2/city/lookup",
     "pos": ["location"],
     "opts": [("adm", False, None, None, "上级行政区划，过滤重名"),
              ("range", False, None, None, "ISO 3166 国家代码，限定搜索范围"),
              ("number", False, "10", None, "返回数量 1-20"),
              ("lang", False, "zh", None, "语言")],
     "help": "城市搜索，返回 LocationID"},
    {"name": "top", "host": "geo", "path": "/geo/v2/city/top",
     "pos": [],
     "opts": [("location", False, None, None, "可选：定位所属国家/地区的热门城市"),
              ("number", False, "10", None, "返回数量 1-20"),
              ("lang", False, "zh", None, "语言")],
     "help": "热门城市列表"},
    {"name": "poi", "host": "geo", "path": "/geo/v2/poi/lookup",
     "pos": ["location"],
     "opts": [("type", False, "scenic", ["scenic", "cul", "gov", "edu", "hosp", "bus", "cbd", "ntour", "tower"], "POI 类型"),
              ("number", False, "10", None, "返回数量 1-20"),
              ("lang", False, "zh", None, "语言")],
     "help": "POI 搜索（景点/文化/政府/教育/医院/交通等），location 建议用 经度,纬度"},
    {"name": "poi-range", "host": "geo", "path": "/geo/v2/poi/range",
     "pos": ["location"],
     "opts": [("type", False, "scenic", ["scenic", "cul", "gov", "edu", "hosp", "bus", "cbd", "ntour", "tower"], "POI 类型"),
              ("radius", False, "5", None, "搜索半径（公里）"),
              ("number", False, "10", None, "返回数量 1-20"),
              ("lang", False, "zh", None, "语言")],
     "help": "POI 范围搜索（以经纬度为中心）"},

    # ---- 天气 ----
    {"name": "now", "host": "main", "path": "/v7/weather/now",
     "pos": ["location"],
     "opts": [("lang", False, "zh", None, "语言")],
     "help": "实时天气"},
    {"name": "hourly", "host": "main", "path": "/v7/weather/{hours}h",
     "pos": ["location"],
     "opts": [("hours", False, "24", ["24", "72", "168"], "小时数"),
              ("lang", False, "zh", None, "语言")],
     "help": "逐小时预报（24/72/168 小时）"},
    {"name": "daily", "host": "main", "path": "/v7/weather/{days}d",
     "pos": ["location"],
     "opts": [("days", False, "7", ["3", "7", "15", "30"], "天数"),
              ("lang", False, "zh", None, "语言")],
     "help": "每日预报（3/7/15/30 天）"},
    {"name": "minutely", "host": "main", "path": "/v7/minutely/5m",
     "pos": ["location"], "resolve_latlon": True,
     "opts": [("lang", False, "zh", None, "语言")],
     "help": "分钟级降水（临近预报，中国 1km 精度，自动解析为经纬度）"},
    {"name": "warning", "host": "main", "path": "/weatheralert/v1/current/{lat}/{lon}",
     "pos": ["location"], "latlon_path": True,
     "opts": [("lang", False, "zh", None, "语言")],
     "help": "实时天气预警（新版 v1，自动解析为经纬度）"},
    {"name": "indices", "host": "main", "path": "/v7/indices/{period}",
     "pos": ["location"],
     "opts": [("type", False, "0", None, "指数类型，如 1,3,9；0=全部"),
              ("period", False, "1d", ["1d", "3d"], "周期"),
              ("lang", False, "zh", None, "语言")],
     "help": "生活指数（1d 或 3d）"},

    # ---- 空气质量（新版 airquality v1，需经纬度）----
    {"name": "air", "host": "main", "path": "/airquality/v1/current/{lat}/{lon}",
     "pos": ["location"], "latlon_path": True,
     "opts": [("lang", False, "zh", None, "语言")],
     "help": "空气质量实况（新版 v1）"},
    {"name": "air-hourly", "host": "main", "path": "/airquality/v1/hourly/{lat}/{lon}",
     "pos": ["location"], "latlon_path": True,
     "opts": [("lang", False, "zh", None, "语言")],
     "help": "空气质量逐小时预报（未来 24h）"},
    {"name": "air-daily", "host": "main", "path": "/airquality/v1/daily/{lat}/{lon}",
     "pos": ["location"], "latlon_path": True,
     "opts": [("lang", False, "zh", None, "语言")],
     "help": "空气质量每日预报（未来 3 天）"},

    # ---- 天文 ----
    {"name": "astro-sun", "host": "main", "path": "/v7/astronomy/sun",
     "pos": ["location"],
     "opts": [("date", False, None, None, "日期 yyyyMMdd（默认可查今日）"),
              ("lang", False, "zh", None, "语言")],
     "help": "日出日落（未来 60 天）"},
    {"name": "astro-moon", "host": "main", "path": "/v7/astronomy/moon",
     "pos": ["location"],
     "opts": [("date", False, None, None, "日期 yyyyMMdd"),
              ("lang", False, "zh", None, "语言")],
     "help": "月升月落和月相（未来 60 天）"},
    {"name": "astro-solar", "host": "main", "path": "/v7/astronomy/solar-elevation-angle",
     "pos": ["location"], "resolve_latlon": True,
     "opts": [("date", False, None, None, "日期 yyyyMMdd"),
              ("time", False, "1200", None, "时间 HHmm（计算该时刻高度角）"),
              ("tz", False, "0800", None, "时区偏移，如 0800（注意 QWeather 要求 HHmm 格式，非 +08:00）"),
              ("alt", False, "0", None, "海拔（米）"),
              ("lang", False, "zh", None, "语言")],
     "help": "太阳高度角与方位角（需 tz 与 alt）"},

    # ---- 历史时光机 ----
    {"name": "historical", "host": "main", "path": "/v7/historical/weather",
     "pos": ["location"],
     "opts": [("date", False, None, None, "日期 yyyyMMdd（最近 10 天内，不含今天）"),
              ("unit", False, "m", ["m", "i"], "单位 m=公制 / i=英制"),
              ("lang", False, "zh", None, "语言")],
     "help": "历史天气时光机（最近 10 天再分析数据）"},
    {"name": "historical-air", "host": "main", "path": "/v7/historical/air",
     "pos": ["location"],
     "opts": [("date", False, None, None, "日期 yyyyMMdd"),
              ("unit", False, "m", ["m", "i"], "单位"),
              ("lang", False, "zh", None, "语言")],
     "help": "历史空气质量时光机"},

    # ---- 太阳辐射 ----
    {"name": "solar", "host": "main", "path": "/solarradiation/v1/forecast/{lat}/{lon}",
     "pos": ["location"], "latlon_path": True,
     "opts": [("lang", False, "zh", None, "语言")],
     "help": "太阳辐射预报（新版 v1，自动解析为经纬度）"},

    # ---- 台风（热带气旋）----
    {"name": "tropical-list", "host": "main", "path": "/v7/tropical/storm-list",
     "pos": [],
     "opts": [("basin", False, "NP", None, "流域：NP=西北太平洋（目前仅支持）"),
              ("year", False, None, None, "年份（今年或去年，如 2026）"),
              ("lang", False, "zh", None, "语言")],
     "help": "台风列表（近 2 年）"},
    {"name": "tropical-track", "host": "main", "path": "/v7/tropical/storm-track",
     "pos": ["stormid"],
     "opts": [("lang", False, "zh", None, "语言")],
     "help": "台风实况和路径（stormid 来自列表）"},
    {"name": "tropical-forecast", "host": "main", "path": "/v7/tropical/storm-forecast",
     "pos": ["stormid"],
     "opts": [("lang", False, "zh", None, "语言")],
     "help": "台风预报路径"},

    # ---- 海洋 ----
    {"name": "tide", "host": "main", "path": "/v7/ocean/tide",
     "pos": ["location"],
     "opts": [("date", False, None, None, "日期 yyyyMMdd（未来 10 天）"),
              ("lang", False, "zh", None, "语言")],
     "help": "潮汐（需潮汐站 LocationID，用 poi 搜索获取）"},
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="QWeather (和风天气) API client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", default="devapi.qweather.com",
                        help="天气 API host（免费版默认 devapi.qweather.com；商业版填 your-xxx.qweatherapi.com）")
    parser.add_argument("--geo-host", default=None, help="GeoAPI host（默认自动推断）")
    parser.add_argument("--auth", choices=["jwt", "apikey"], default="apikey")
    parser.add_argument("--apikey", default=None, help="API Key（--auth apikey）")
    parser.add_argument("--key-path", default=None, help="Ed25519 私钥 PEM 路径（--auth jwt）")
    parser.add_argument("--kid", default=None, help="凭据 ID（--auth jwt）")
    parser.add_argument("--sub", default=None, help="项目 ID（--auth jwt）")
    parser.add_argument("--raw", action="store_true", help="输出未格式化 JSON")
    parser.add_argument("--print-token", action="store_true",
                        help="仅打印生成的 JWT 并退出（用于调试，不发起请求）")

    sub = parser.add_subparsers(dest="cmd", required=False)
    for ep in ENDPOINTS:
        p = sub.add_parser(ep["name"], help=ep["help"])
        for pos_name in ep["pos"]:
            p.add_argument(pos_name, help=f"{pos_name}（LocationID 或 经度,纬度）")
        for (name, required, default, choices, help_) in ep["opts"]:
            kw = {"default": default, "help": help_}
            if choices:
                kw["choices"] = choices
            p.add_argument("--" + name, **kw)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    auth_header = resolve_auth(args)

    if args.print_token:
        if args.auth != "jwt":
            sys.stderr.write("--print-token 仅用于 JWT 模式\n")
            sys.exit(2)
        token = make_jwt(args.key_path, args.kid, args.sub)
        print(token)
        return

    if args.cmd is None:
        parser.error("缺少子命令（或使用 --print-token 仅打印 JWT）")

    ep = next((e for e in ENDPOINTS if e["name"] == args.cmd), None)
    if ep is None:
        parser.error("未知命令")

    # 路径变量填充（lat/lon 留待下方按 latlon_path 处理）
    path = ep["path"]
    for var in re.findall(r"\{(\w+)\}", path):
        if var in ("lat", "lon"):
            continue
        path = path.replace("{" + var + "}", str(getattr(args, var)))

    # 查询参数组装
    params = {}
    if ep.get("latlon_path"):
        lat, lon = resolve_latlon(getattr(args, ep["pos"][0]), auth_header, args.host)
        path = path.replace("{lat}", "%.2f" % lat).replace("{lon}", "%.2f" % lon)
    elif ep.get("resolve_latlon"):
        lat, lon = resolve_latlon(getattr(args, ep["pos"][0]), auth_header, args.host)
        params[ep["pos"][0]] = "%.2f,%.2f" % (lon, lat)  # QWeather location = 经度,纬度
    else:
        for pos_name in ep["pos"]:
            val = getattr(args, pos_name)
            if pos_name == "location" and ep["name"] not in ("lookup", "poi", "poi-range", "tide"):
                # 天气/天文/历史接口 location 不接受中文城市名，统一解析为 经度,纬度
                params[pos_name] = resolve_location_to_param(val, auth_header, args.host)
            else:
                params[pos_name] = val

    for (name, required, default, choices, help_) in ep["opts"]:
        val = getattr(args, name)
        if val is not None:
            params[name] = val

    # 天文端点：date 缺省时补今天（solar-elevation-angle 必填）
    if ep["name"].startswith("astro") and "date" not in params:
        params["date"] = datetime.date.today().strftime("%Y%m%d")

    host = geo_base_host(args.host, args.geo_host) if ep["host"] == "geo" else args.host
    data = http_get(host, path, params, auth_header)
    report(data, args.raw)


if __name__ == "__main__":
    main()

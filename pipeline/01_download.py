#!/usr/bin/env python3
"""
01_download.py — 下载「流感季公营医院急症服务压力」研究所需的全部原始数据。

数据来源（全部为公开数据）：
    卫生署 卫生防护中心      流感速递图表数据            (CSV)
    医院管理局               服务需求高峰统计数字        (JSON)
    医院管理局               病床数目                   (JSON)
    医院管理局               急症室年服务量              (JSON)
    医院管理局               医院/机构名录 + 坐标        (JSON)
    香港天文台               逐日平均/最高/最低气温       (CSV)
    data.gov.hk              以上数据集的元数据（出处存档）(JSON)

用法：
    python pipeline/01_download.py              # 增量下载；已存在且校验通过则跳过
    python pipeline/01_download.py --force      # 强制重新下载全部
    python pipeline/01_download.py --check      # 只校验本地文件，不联网

输出：
    data/raw/...              原始文件（逐字节保存，不做任何改动）
    data/raw/_manifest.json   每个文件的 URL / 字节数 / SHA256 / 抓取时间
    data/raw/_provenance.json data.gov.hk 数据集的官方元数据

设计原则：
    1. 原始文件只下载不改写。任何清洗都发生在 02_build.py。
    2. 幂等：重复执行不会产生不同结果；--check 可离线验证完整性。
    3. 记录 SHA256，使下游结果可与具体数据版本一一对应。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# --------------------------------------------------------------------------
# 路径
# --------------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "_manifest.json"
PROVENANCE = RAW / "_provenance.json"

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )
}
TIMEOUT = 120
RETRIES = 3

# 部分政府站点会对 Python 的 TLS 指纹返回 SSL UNEXPECTED_EOF，而 curl 可正常握手。
# 因此 Python 重试耗尽后回退到 curl，使下载在更多网络环境下可用。

# --------------------------------------------------------------------------
# 1. 静态清单：每个 (URL, 本地相对路径)
# --------------------------------------------------------------------------
HKO_BASE = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
HKO_DATA_TYPES = {
    "CLMTEMP": "temp_mean",   # 日平均气温 (°C)
    "CLMMAXT": "temp_max",    # 日最高气温 (°C)
    "CLMMINT": "temp_min",    # 日最低气温 (°C)
}
HKO_YEARS = list(range(2019, 2027))   # 覆盖面板期间 2019-12 ~ 2026-08
HKO_STATION = "HKO"                    # 香港天文台总部


def build_manifest() -> list[dict]:
    """返回全部待下载资源的清单。"""
    items: list[dict] = []

    def add(url: str, relpath: str, note: str) -> None:
        items.append({"url": url, "path": relpath, "note": note})

    # -- 卫生署：流感速递 -----------------------------------------------------
    add(
        "https://www.chp.gov.hk/files/misc/flux_data.csv",
        "flu/flux_data.csv",
        "流感速递图表数据（周）— 数据源：hk-dh-chpsebcddr-flu-express",
    )

    # -- 医院管理局：服务需求高峰统计数字 --------------------------------------
    add(
        "https://www.ha.org.hk/opendata/pas_report/Daily_Services_Statistics/"
        "Daily_Services_Statistics_EN.json",
        "ha/service_demand_surge_daily.json",
        "HA 服务需求高峰统计（逐日 × 医院）— hospital-hadata-key-statistics-during-surge",
    )

    # -- 医院管理局：病床数目 --------------------------------------------------
    add(
        "https://www.ha.org.hk/opendata/hosp-bed-en.json",
        "ha/hospital_beds.json",
        "HA 按专科及联网/医院划分的病床数目（财政年度）— hospital-hadata-service-ipdp",
    )

    # -- 医院管理局：急症室年服务量 --------------------------------------------
    add(
        "https://www.ha.org.hk/opendata/ae-attnd-en.json",
        "ha/ae_attendances_annual.json",
        "HA 按联网/医院划分的急症室求诊人次（财政年度）— hospital-hadata-service-ambulatory-community",
    )

    # -- 医院管理局：设施名录与坐标 --------------------------------------------
    add(
        "https://www.ha.org.hk/opendata/facility-hosp.json",
        "ha/facility_hospitals.json",
        "HA 医院/机构名录、联网归属、经纬度 — hospital-hadata-health-care-facilities",
    )

    # -- 香港天文台：逐日气温 --------------------------------------------------
    for code, name in HKO_DATA_TYPES.items():
        for year in HKO_YEARS:
            qs = urllib.parse.urlencode(
                {
                    "dataType": code,
                    "lang": "en",
                    "rformat": "csv",
                    "year": year,
                    "station": HKO_STATION,
                }
            )
            add(
                f"{HKO_BASE}?{qs}",
                f"hko/{code}_{year}.csv",
                f"HKO 逐日{name} {year} 年（{code}）",
            )

    return items


# --------------------------------------------------------------------------
# 2. data.gov.hk 数据集元数据（出处存档）
# --------------------------------------------------------------------------
PROVENANCE_PACKAGES = [
    "hk-dh-chpsebcddr-flu-express",
    "hospital-hadata-key-statistics-during-surge",
    "hospital-hadata-service-ipdp",
    "hospital-hadata-service-ambulatory-community",
    "hospital-hadata-health-care-facilities",
]

# --------------------------------------------------------------------------
# 3. 工具函数
# --------------------------------------------------------------------------
def _fetch_urllib(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _fetch_curl(url: str) -> bytes:
    """回退方案：调用系统 curl。对 Python TLS 指纹不友好的站点有效。"""
    if not shutil.which("curl"):
        raise RuntimeError("系统没有 curl，无法回退")
    proc = subprocess.run(
        ["curl", "-sSL", "--fail", "--max-time", str(TIMEOUT),
         "-H", f"User-Agent: {UA['User-Agent']}", url],
        capture_output=True,
        timeout=TIMEOUT + 30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"curl 退出码 {proc.returncode}：{proc.stderr.decode('utf-8', 'ignore')[:200]}")
    if not proc.stdout:
        raise RuntimeError("curl 返回空内容")
    return proc.stdout


def http_get(url: str) -> bytes:
    """先试 Python 原生下载，耗尽重试后回退到 curl。"""
    last: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            return _fetch_urllib(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last = exc
            if attempt < RETRIES:
                time.sleep(2 ** attempt)

    try:
        body = _fetch_curl(url)
        print(f"      （Python TLS 失败，已用 curl 回退成功：{type(last).__name__}）")
        return body
    except Exception as curl_exc:  # noqa: BLE001
        raise RuntimeError(
            f"下载失败：Python 重试 {RETRIES} 次 + curl 回退均失败\n"
            f"  Python 错误：{last}\n  curl 错误：{curl_exc}"
        ) from last


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sanity_check(url: str, body: bytes) -> None:
    """拦截明显的错误响应（HKO 参数错误 / HTML 错误页）。"""
    head = body[:600].decode("utf-8", "ignore")
    if url.startswith(HKO_BASE) and "Please include valid parameters" in head:
        raise RuntimeError(f"HKO 接口参数无效：{url}")
    if body[:15].lstrip().lower().startswith(b"<!doctype html") and not url.endswith(".json"):
        raise RuntimeError(f"返回 HTML 而非数据（可能 404）：{url}")


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"generated_at": None, "files": {}}


def save_manifest(manifest: dict) -> None:
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


# --------------------------------------------------------------------------
# 4. 主流程
# --------------------------------------------------------------------------
def cmd_check() -> int:
    """离线校验：本地文件是否齐全、SHA256 是否与清单一致。"""
    manifest = load_manifest()
    entries = manifest.get("files", {})
    if not entries:
        print("找不到 data/raw/_manifest.json —— 请先执行一次下载。")
        return 1

    print(f"校验 {len(entries)} 个文件……\n")
    bad: list[str] = []
    for relpath, meta in sorted(entries.items()):
        path = RAW / relpath
        if not path.exists():
            print(f"  [缺失] {relpath}")
            bad.append(relpath)
            continue
        digest = sha256_file(path)
        if digest != meta["sha256"]:
            print(f"  [校验失败] {relpath}\n      期望 {meta['sha256']}\n      实际 {digest}")
            bad.append(relpath)
        else:
            print(f"  [OK] {relpath:44s} {meta['bytes']:>10,} bytes")

    print()
    if bad:
        print(f"✗ {len(bad)} 个文件有问题。执行 `--force` 重新下载。")
        return 1
    print(f"✓ 全部 {len(entries)} 个文件校验通过。")
    return 0


def cmd_download(force: bool) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    items = build_manifest()
    manifest = load_manifest()
    files = manifest.setdefault("files", {})

    n_ok = n_skip = n_fail = 0
    for i, item in enumerate(items, 1):
        url, relpath = item["url"], item["path"]
        dest = RAW / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists() and not force:
            recorded = files.get(relpath)
            if recorded and recorded.get("sha256") == sha256_file(dest):
                print(f"[{i:>2}/{len(items)}] 跳过（已存在且校验通过）  {relpath}")
                n_skip += 1
                continue

        try:
            body = http_get(url)
            sanity_check(url, body)
        except RuntimeError as exc:
            print(f"[{i:>2}/{len(items)}] ✗ {relpath}\n      {exc}")
            n_fail += 1
            continue

        dest.write_bytes(body)
        files[relpath] = {
            "url": url,
            "note": item["note"],
            "bytes": len(body),
            "sha256": sha256(body),
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        print(f"[{i:>2}/{len(items)}] ✓ {relpath:44s} {len(body):>10,} bytes")
        n_ok += 1

    # -- data.gov.hk 元数据存档 -----------------------------------------------
    provenance = {}
    for pkg in PROVENANCE_PACKAGES:
        url = f"https://data.gov.hk/en-data/api/3/action/package_show?id={pkg}"
        try:
            payload = json.loads(http_get(url).decode("utf-8"))
            result = payload.get("result", {})
            provenance[pkg] = {
                "title": result.get("title"),
                "organization": (result.get("organization") or {}).get("title"),
                "notes": result.get("notes"),
                "update_frequency": result.get("frequency") or result.get("update_frequency"),
                "url": f"https://data.gov.hk/en-data/dataset/{pkg}",
                "resource_count": len(result.get("resources", [])),
            }
            print(f"[元数据] ✓ {pkg}")
        except Exception as exc:  # noqa: BLE001 — 元数据失败不应中断主流程
            print(f"[元数据] ✗ {pkg}: {exc}")
            provenance[pkg] = {"error": str(exc)}

    PROVENANCE.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest["source_count"] = len(files)
    save_manifest(manifest)

    print()
    print(f"下载完成：新增/更新 {n_ok}，跳过 {n_skip}，失败 {n_fail}")
    print(f"清单：{MANIFEST.relative_to(ROOT)}")
    print(f"元数据：{PROVENANCE.relative_to(ROOT)}")
    return 1 if n_fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="强制重新下载全部文件")
    ap.add_argument("--check", action="store_true", help="只做离线校验，不联网")
    args = ap.parse_args()

    if args.check:
        return cmd_check()
    return cmd_download(force=args.force)


if __name__ == "__main__":
    sys.exit(main())

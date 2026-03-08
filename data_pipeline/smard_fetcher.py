# data_pipeline/smard_fetcher.py
#
# SMARD = Bundesnetzagentur resmi elektrik piyasası platformu.
# Token yok, kayıt yok, tamamen açık API.
# Sadece DE için üretim karması (solar, wind, hydro, coal, gas, nuclear) çeker.
# Fiyat verisi için artık energy_charts_fetcher.py kullanılıyor.

import requests
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import time

BASE = "https://www.smard.de/app/chart_data"

FILTERS = {
    "solar":    4068,
    "wind_on":  4067,
    "wind_off": 1225,
    "hydro":    1226,
    "coal":     1223,
    "gas":      4071,
    "nuclear":  1224,
}

REGION     = "DE"
RESOLUTION = "hour"


def get_db():
    client = MongoClient("mongodb://localhost:27017")
    return client["electricity_tracker"]


def _get_latest_timestamp(filter_id: int) -> int:
    url = f"{BASE}/{filter_id}/{REGION}/index_{RESOLUTION}.json"
    r   = requests.get(url, timeout=15)
    r.raise_for_status()
    timestamps = r.json().get("timestamps", [])
    return timestamps[-1] if timestamps else None


def _fetch_series(filter_id: int, timestamp: int) -> list:
    url = f"{BASE}/{filter_id}/{REGION}/{filter_id}_{REGION}_{RESOLUTION}_{timestamp}.json"
    r   = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json().get("series", [])


def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(tzinfo=None)


def fetch_and_save_generation(hours_back: int = 48) -> int:
    db        = get_db()
    cutoff_ms = (time.time() - hours_back * 3600) * 1000

    ts_on    = _get_latest_timestamp(FILTERS["wind_on"])
    ts_off   = _get_latest_timestamp(FILTERS["wind_off"])
    wind_on  = {ms: v for ms, v in _fetch_series(FILTERS["wind_on"],  ts_on)  if ms and v is not None}
    wind_off = {ms: v for ms, v in _fetch_series(FILTERS["wind_off"], ts_off) if ms and v is not None}
    all_wind = {ms: wind_on.get(ms, 0) + wind_off.get(ms, 0)
                for ms in set(wind_on) | set(wind_off)}

    raw = {"wind": all_wind}
    for src, fid in [("solar",   FILTERS["solar"]),
                     ("hydro",   FILTERS["hydro"]),
                     ("coal",    FILTERS["coal"]),
                     ("gas",     FILTERS["gas"]),
                     ("nuclear", FILTERS["nuclear"])]:
        ts_latest = _get_latest_timestamp(fid)
        raw[src]  = {ms: v for ms, v in _fetch_series(fid, ts_latest) if ms and v is not None}

    all_ts = set()
    for d in raw.values():
        all_ts.update(d.keys())

    saved = 0
    for ms in sorted(all_ts):
        if ms < cutoff_ms:
            continue
        dt  = _ms_to_dt(ms)
        doc = {
            "country":   "DE",
            "timestamp": dt,
            "solar":     raw["solar"].get(ms, 0),
            "wind":      raw["wind"].get(ms, 0),
            "hydro":     raw["hydro"].get(ms, 0),
            "coal":      raw["coal"].get(ms, 0),
            "gas":       raw["gas"].get(ms, 0),
            "nuclear":   raw["nuclear"].get(ms, 0),
        }
        db.generation_mix.update_one(
            {"country": "DE", "timestamp": dt},
            {"$set": doc},
            upsert=True,
        )
        saved += 1

    print(f"[DE] {saved} üretim kaydı kaydedildi.")
    return saved


def run():
    print(f"\n[{datetime.utcnow().isoformat()}] SMARD üretim fetch başlıyor...")
    try:
        fetch_and_save_generation(hours_back=48)
    except Exception as e:
        print(f"[SMARD] Hata: {e}")
    print("Tamamlandı.")


if __name__ == "__main__":
    run()
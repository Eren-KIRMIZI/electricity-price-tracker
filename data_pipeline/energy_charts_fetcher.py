# data_pipeline/energy_charts_fetcher.py
#
# Fraunhofer ISE — Energy-Charts API
# Token yok, kayıt yok, tamamen açık.
# Endpoint: https://api.energy-charts.info/price?bzn={BZN}&start={ISO}&end={ISO}
# Response: { "unix_seconds": [...], "price": [...] }
#
# Desteklenen ülkeler ve bidding zone kodları:
#   DE → DE-LU  |  FR → FR  |  IT → IT-NORTH  |  ES → ES  |  PL → PL

import requests
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

BASE_URL = "https://api.energy-charts.info/price"

COUNTRY_TO_BZN = {
    "DE": "DE-LU",
    "FR": "FR",
    "IT": "IT-NORTH",
    "ES": "ES",
    "PL": "PL",
}

HEADERS = {
    "User-Agent": "ElectricityTracker/1.0 (research project)",
    "Accept": "application/json",
}


def get_db():
    client = MongoClient("mongodb://localhost:27017")
    return client["electricity_tracker"]


def fetch_prices(country: str, hours_back: int = 48) -> list:
    """
    Energy-Charts API'den son `hours_back` saatlik fiyat verisini çeker.
    Döner: [{"country": "DE", "timestamp": datetime, "price_eur_mwh": float}, ...]
    """
    bzn = COUNTRY_TO_BZN.get(country.upper())
    if not bzn:
        raise ValueError(f"Desteklenmeyen ülke: {country}. Desteklenenler: {list(COUNTRY_TO_BZN)}")

    now   = datetime.now(timezone.utc)
    start = (now - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:00Z")
    end   = now.strftime("%Y-%m-%dT%H:00Z")

    params   = {"bzn": bzn, "start": start, "end": end}
    response = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
    response.raise_for_status()
    data = response.json()

    unix_seconds = data.get("unix_seconds", [])
    prices       = data.get("price", [])

    if not unix_seconds or not prices:
        print(f"[{country}] Boş yanıt geldi.")
        return []

    records = []
    for ts, price in zip(unix_seconds, prices):
        if ts is None or price is None:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
        records.append({
            "country":       country.upper(),
            "timestamp":     dt,
            "price_eur_mwh": float(price),
        })

    return records


def save_prices(records: list):
    """Fiyat kayıtlarını MongoDB'ye upsert ile kaydeder."""
    if not records:
        return
    db = get_db()
    for r in records:
        db.electricity_prices.update_one(
            {"country": r["country"], "timestamp": r["timestamp"]},
            {"$set": r},
            upsert=True,
        )


def fetch_and_save(country: str, hours_back: int = 48) -> int:
    """Belirtilen ülke için fiyat çekip kaydeder. Kaydedilen kayıt sayısını döner."""
    try:
        records = fetch_prices(country, hours_back)
        save_prices(records)
        print(f"[{country}] {len(records)} fiyat kaydı kaydedildi.")
        return len(records)
    except Exception as e:
        print(f"[{country}] Hata: {e}")
        return 0


def fetch_all(hours_back: int = 48):
    """Tüm desteklenen ülkeler için fiyat verisini çekip kaydeder."""
    print(f"\n[{datetime.utcnow().isoformat()}] Energy-Charts fetch başlıyor...")
    total = 0
    for country in COUNTRY_TO_BZN:
        total += fetch_and_save(country, hours_back)
    print(f"Toplam: {total} kayıt kaydedildi.\n")


if __name__ == "__main__":
    fetch_all(hours_back=48)
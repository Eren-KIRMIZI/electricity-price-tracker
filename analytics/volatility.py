# analytics/volatility.py
from pymongo import MongoClient
from datetime import datetime, timedelta
import statistics

def get_db():
    client = MongoClient("mongodb://localhost:27017")
    return client["electricity_tracker"]

def get_price_volatility(country: str, hours: int = 24) -> dict:
    db        = get_db()
    since     = datetime.utcnow() - timedelta(hours=hours)

    docs = list(db.electricity_prices.find(
        {"country": country.upper(), "timestamp": {"$gte": since}},
        {"price_eur_mwh": 1, "_id": 0}
    ))

    if len(docs) < 2:
        return {}

    prices = [d["price_eur_mwh"] for d in docs]
    avg    = statistics.mean(prices)
    std    = statistics.stdev(prices)
    mx     = max(prices)
    mn     = min(prices)

    return {
        "country":                country.upper(),
        "period_hours":           hours,
        "std_dev":                round(std, 4),
        "avg_price":              round(avg, 4),
        "max_price":              round(mx, 4),
        "min_price":              round(mn, 4),
        "coefficient_of_variation": round(std / avg * 100, 2) if avg > 0 else 0,
        "spike_threshold":        round(avg * 1.5, 4),
        "num_records":            len(prices)
    }

def detect_price_spikes(country: str, hours: int = 24) -> list:
    db    = get_db()
    since = datetime.utcnow() - timedelta(hours=hours)

    docs = list(db.electricity_prices.find(
        {"country": country.upper(), "timestamp": {"$gte": since}},
        {"timestamp": 1, "price_eur_mwh": 1, "_id": 0}
    ).sort("timestamp", 1))

    if not docs:
        return []

    avg       = statistics.mean(d["price_eur_mwh"] for d in docs)
    threshold = avg * 1.5

    return [
        {
            "timestamp": d["timestamp"].isoformat(),
            "price":     d["price_eur_mwh"],
            "avg_price": round(avg, 4),
            "ratio":     round(d["price_eur_mwh"] / avg, 2)
        }
        for d in docs if d["price_eur_mwh"] > threshold
    ]

if __name__ == "__main__":
    for c in ["DE", "FR", "IT", "TR"]:
        v = get_price_volatility(c)
        if v:
            print(f"{c}: avg={v['avg_price']} std={v['std_dev']} CV={v['coefficient_of_variation']}%")
        spikes = detect_price_spikes(c)
        if spikes:
            print(f"  {len(spikes)} spike(s) detected")
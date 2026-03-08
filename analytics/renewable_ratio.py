# analytics/renewable_ratio.py
from pymongo import MongoClient
from datetime import datetime, timedelta

def get_db():
    client = MongoClient("mongodb://localhost:27017")
    return client["electricity_tracker"]

def get_renewable_ratio(country: str, hours: int = 24) -> dict:
    db    = get_db()
    since = datetime.utcnow() - timedelta(hours=hours)

    pipeline = [
        {"$match": {
            "country":   country.upper(),
            "timestamp": {"$gte": since}
        }},
        {"$group": {
            "_id":           None,
            "avg_solar":     {"$avg": "$solar"},
            "avg_wind":      {"$avg": "$wind"},
            "avg_hydro":     {"$avg": "$hydro"},
            "avg_coal":      {"$avg": "$coal"},
            "avg_gas":       {"$avg": "$gas"},
            "avg_nuclear":   {"$avg": "$nuclear"},
        }}
    ]

    result = list(db.generation_mix.aggregate(pipeline))
    if not result:
        return {}

    r     = result[0]
    total = r["avg_solar"] + r["avg_wind"] + r["avg_hydro"] + \
            r["avg_coal"]  + r["avg_gas"]  + r["avg_nuclear"]

    if total == 0:
        return {}

    return {
        "country":              country.upper(),
        "period_hours":         hours,
        "renewable_ratio_pct":  round((r["avg_solar"] + r["avg_wind"] + r["avg_hydro"]) / total * 100, 2),
        "sources": {
            "solar_pct":   round(r["avg_solar"]   / total * 100, 2),
            "wind_pct":    round(r["avg_wind"]     / total * 100, 2),
            "hydro_pct":   round(r["avg_hydro"]    / total * 100, 2),
            "coal_pct":    round(r["avg_coal"]     / total * 100, 2),
            "gas_pct":     round(r["avg_gas"]      / total * 100, 2),
            "nuclear_pct": round(r["avg_nuclear"]  / total * 100, 2),
        }
    }

def get_renewable_trend(country: str, days: int = 7) -> list:
    db    = get_db()
    since = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {
            "country":   country.upper(),
            "timestamp": {"$gte": since}
        }},
        {"$group": {
            "_id": {
                "year":  {"$year":  "$timestamp"},
                "month": {"$month": "$timestamp"},
                "day":   {"$dayOfMonth": "$timestamp"}
            },
            "avg_renewable": {"$avg": {"$add": ["$solar", "$wind", "$hydro"]}},
            "avg_total":     {"$avg": {"$add": ["$solar", "$wind", "$hydro", "$coal", "$gas", "$nuclear"]}}
        }},
        {"$sort": {"_id": 1}}
    ]

    rows  = list(db.generation_mix.aggregate(pipeline))
    trend = []
    for row in rows:
        total = row["avg_total"]
        if total and total > 0:
            date_str = f"{row['_id']['year']}-{row['_id']['month']:02d}-{row['_id']['day']:02d}"
            trend.append({
                "date":                date_str,
                "renewable_ratio_pct": round(row["avg_renewable"] / total * 100, 2)
            })
    return trend

if __name__ == "__main__":
    for c in ["DE", "FR", "IT", "TR"]:
        ratio = get_renewable_ratio(c)
        if ratio:
            print(f"{c}: {ratio['renewable_ratio_pct']}% renewable")
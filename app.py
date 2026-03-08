# app.py
#
# Veri kaynakları (token yok, kayıt yok):
#   Fiyat (DE, FR, IT, ES, PL) → Energy-Charts API (Fraunhofer ISE)
#   Üretim karması (DE)        → SMARD (Bundesnetzagentur)


from flask import Flask, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
import threading
import time as _time

app = Flask(__name__)
CORS(app)

SUPPORTED_COUNTRIES = ["DE", "FR", "IT", "ES", "PL"]


def get_db():
    client = MongoClient("mongodb://localhost:27017")
    return client["electricity_tracker"]


def _fetch_prices_bg():
    try:
        from data_pipeline.energy_charts_fetcher import fetch_all
        fetch_all(hours_back=48)
    except Exception as e:
        print(f"[PriceFetch] Hata: {e}")


def _fetch_generation_bg():
    try:
        from data_pipeline.smard_fetcher import run
        run()
    except Exception as e:
        print(f"[GenFetch] Hata: {e}")


def _scheduler():
    """Her 60 dakikada bir veriyi günceller."""
    while True:
        _time.sleep(3600)
        print(f"[Scheduler] {datetime.utcnow().isoformat()}")
        _fetch_prices_bg()
        _fetch_generation_bg()


# Uygulama başlangıcında fetch + sürekli scheduler
threading.Thread(target=_fetch_prices_bg,     daemon=True).start()
threading.Thread(target=_fetch_generation_bg, daemon=True).start()
threading.Thread(target=_scheduler,           daemon=True).start()


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/prices/<country>")
def get_prices(country):
    country = country.upper()
    if country not in SUPPORTED_COUNTRIES:
        return jsonify({"error": "Desteklenmiyor"}), 400

    db    = get_db()
    since = datetime.utcnow() - timedelta(hours=24)
    docs  = list(db.electricity_prices.find(
        {"country": country, "timestamp": {"$gte": since}},
        {"timestamp": 1, "price_eur_mwh": 1, "_id": 0}
    ).sort("timestamp", 1))

    if not docs:
        return jsonify([])

    return jsonify([
        {"time": d["timestamp"].isoformat(), "price": d["price_eur_mwh"]}
        for d in docs
    ])


@app.route("/api/generation/<country>")
def get_generation(country):
    country = country.upper()
    if country != "DE":
        return jsonify({})

    db  = get_db()
    doc = db.generation_mix.find_one(
        {"country": "DE"},
        {"solar": 1, "wind": 1, "coal": 1, "gas": 1, "hydro": 1, "nuclear": 1, "_id": 0},
        sort=[("timestamp", -1)]
    )
    return jsonify(doc or {})


@app.route("/api/comparison")
def get_comparison():
    db    = get_db()
    since = datetime.utcnow() - timedelta(hours=24)

    pipeline = [
        {"$match": {"country": {"$in": SUPPORTED_COUNTRIES}, "timestamp": {"$gte": since}}},
        {"$group": {"_id": "$country", "avg_price": {"$avg": "$price_eur_mwh"}}},
        {"$sort":  {"avg_price": -1}}
    ]
    rows = list(db.electricity_prices.aggregate(pipeline))
    return jsonify([
        {"country": r["_id"], "avg_price": round(r["avg_price"], 2)}
        for r in rows
    ])


@app.route("/api/volatility/<country>")
def get_volatility(country):
    country = country.upper()
    if country not in SUPPORTED_COUNTRIES:
        return jsonify({}), 400

    from analytics.volatility import get_price_volatility
    result = get_price_volatility(country)
    return jsonify(result or {})


@app.route("/api/renewable/<country>")
def get_renewable(country):
    country = country.upper()
    if country != "DE":
        return jsonify({"renewable_ratio": None})

    from analytics.renewable_ratio import get_renewable_ratio
    r = get_renewable_ratio(country)
    return jsonify({"renewable_ratio": r.get("renewable_ratio_pct", 0) if r else None})


@app.route("/api/predict/<country>")
def get_prediction(country):
    country = country.upper()
    if country not in SUPPORTED_COUNTRIES:
        return jsonify([]), 400

    from analytics.prediction import predict_next_24h
    return jsonify(predict_next_24h(country) or [])


@app.route("/api/status")
def get_status():
    """Her ülke için veri durumu — dashboard badge için."""
    db    = get_db()
    since = datetime.utcnow() - timedelta(hours=3)
    result = {}
    for c in SUPPORTED_COUNTRIES:
        has_p = db.electricity_prices.count_documents(
            {"country": c, "timestamp": {"$gte": since}}, limit=1
        ) > 0
        result[c] = {"prices": has_p}
    result["DE"]["generation"] = db.generation_mix.count_documents(
        {"country": "DE", "timestamp": {"$gte": since}}, limit=1
    ) > 0
    return jsonify(result)


@app.route("/api/refresh")
def manual_refresh():
    threading.Thread(target=_fetch_prices_bg,     daemon=True).start()
    threading.Thread(target=_fetch_generation_bg, daemon=True).start()
    return jsonify({"status": "fetching"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
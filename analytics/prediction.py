# analytics/prediction.py
from pymongo import MongoClient
from datetime import datetime, timedelta
import numpy as np
import warnings
warnings.filterwarnings("ignore")


def get_db():
    client = MongoClient("mongodb://localhost:27017")
    return client["electricity_tracker"]


def fetch_price_series(country: str, hours: int = 168) -> list:
    db    = get_db()
    since = datetime.utcnow() - timedelta(hours=hours)

    return list(db.electricity_prices.find(
        {"country": country.upper(), "timestamp": {"$gte": since}},
        {"timestamp": 1, "price_eur_mwh": 1, "_id": 0}
    ).sort("timestamp", 1))


def _difference(series: list, d: int = 1) -> list:
    result = series.copy()
    for _ in range(d):
        result = [result[i] - result[i - 1] for i in range(1, len(result))]
    return result


def _undifference(base_values: list, differenced: list, d: int = 1) -> list:
    result = differenced.copy()
    for _ in range(d):
        last   = base_values[-1]
        undiff = []
        for v in result:
            last = last + v
            undiff.append(last)
        result     = undiff
        base_values = base_values[1:]
    return result


def _fit_ar(series: list, p: int) -> list:
    n  = len(series)
    X  = np.array([series[i:n - p + i] for i in range(p)]).T
    y  = np.array(series[p:])
    coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coeffs.tolist()


def _fit_ma(residuals: list, q: int) -> list:
    n  = len(residuals)
    X  = np.array([residuals[i:n - q + i] for i in range(q)]).T
    y  = np.array(residuals[q:])
    coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coeffs.tolist()


def _arima_forecast(prices: list, p: int = 2, d: int = 1, q: int = 2, steps: int = 24) -> list:
    original    = prices.copy()
    differenced = _difference(prices, d)

    ar_coeffs = _fit_ar(differenced, p)

    ar_fitted = []
    for i in range(p, len(differenced)):
        pred = sum(ar_coeffs[j] * differenced[i - p + j] for j in range(p))
        ar_fitted.append(pred)

    residuals = [differenced[p + i] - ar_fitted[i] for i in range(len(ar_fitted))]

    ma_coeffs = _fit_ma(residuals, q) if len(residuals) > q else [0.0] * q

    history_diff = differenced.copy()
    history_res  = residuals.copy()
    forecasts    = []

    for _ in range(steps):
        ar_part = sum(ar_coeffs[j] * history_diff[-(p - j)] for j in range(p))
        ma_part = sum(ma_coeffs[j] * history_res[-(q - j)] for j in range(q)) if history_res else 0.0
        pred    = ar_part + ma_part

        history_diff.append(pred)
        history_res.append(0.0)
        forecasts.append(pred)

    return _undifference(original[-d:], forecasts, d)


def predict_next_24h(country: str) -> list:
    series_data = fetch_price_series(country, hours=168)

    if len(series_data) < 48:
        return []

    prices  = [float(d["price_eur_mwh"]) for d in series_data]
    last_ts = series_data[-1]["timestamp"]

    forecast = _arima_forecast(prices, p=2, d=1, q=2, steps=24)

    return [
        {
            "timestamp":       (last_ts + timedelta(hours=i + 1)).isoformat(),
            "predicted_price": round(max(0.0, v), 4)
        }
        for i, v in enumerate(forecast)
    ]


if __name__ == "__main__":
    for c in ["DE", "FR"]:
        preds = predict_next_24h(c)
        if preds:
            print(f"{c} next 24h forecast:")
            for p in preds[:6]:
                print(f"  {p['timestamp']}: {p['predicted_price']} EUR/MWh")
import os
import requests
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ── הגדרות ──────────────────────────────────
PRICE_THRESHOLD_ILS = 1190
START_DATE = date(2026, 7, 12)
END_DATE = date(2026, 8, 9)

# ימי יציאה מותרים (0=שני, 1=שלישי, 2=רביעי, 3=חמישי, 4=שישי, 5=שבת, 6=ראשון)
ALLOWED_DEPARTURE_DAYS = {0, 3, 6}  # שני, חמישי, ראשון

# ימי חזרה אסורים
FORBIDDEN_RETURN_DAYS = {4, 5}  # שישי, שבת
# ────────────────────────────────────────────

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def is_valid_pair(outbound_str, return_str):
    """בודק שיציאה ביום מותר וחזרה לא ביום אסור"""
    outbound_day = date.fromisoformat(outbound_str).weekday()
    return_day = date.fromisoformat(return_str).weekday()
    return outbound_day in ALLOWED_DEPARTURE_DAYS and return_day not in FORBIDDEN_RETURN_DAYS

def generate_all_valid_pairs():
    """מייצר את כל הצירופים התקינים"""
    pairs = []
    current = START_DATE
    while current <= END_DATE:
        if current.weekday() in ALLOWED_DEPARTURE_DAYS:
            for nights in [5, 7]:
                ret = current + timedelta(days=nights)
                if ret.weekday() not in FORBIDDEN_RETURN_DAYS:
                    pairs.append((str(current), str(ret), nights))
        current += timedelta(days=1)
    return pairs

def get_todays_pairs(all_pairs):
    """בוחר 6 צירופים להיום לפי אינדקס מתחלף"""
    batch_size = 6
    day_of_year = date.today().timetuple().tm_yday
    start_idx = (day_of_year * batch_size) % len(all_pairs)
    selected = []
    for i in range(batch_size):
        idx = (start_idx + i) % len(all_pairs)
        selected.append(all_pairs[idx])
    return selected

def get_price_serpapi_explore_europe(month):
    """שאילתה אחת לכל אירופה — מחזירה dict של יעד:מחיר"""
    params = {
        "engine": "google_travel_explore",
        "departure_id": "TLV",
        "outbound_date": f"{month}-01",
        "currency": "ILS",
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
        destinations = data.get("destinations", [])
        result = {}
        for d in destinations:
            iata = d.get("code") or d.get("airport_code", "")
            price = d.get("flight_price")
            if iata and price:
                result[iata] = price
        print(f"  explore {month}: התקבלו {len(result)} יעדים")
        return result
    except Exception as e:
        print(f"  שגיאה ב-explore {month}: {e}")
        return {}

def get_price_serpapi_specific(destination, outbound, ret):
    """חיפוש SerpAPI לתאריכים ספציפיים"""
    params = {
        "engine": "google_flights",
        "departure_id": "TLV",
        "arrival_id": destination,
        "outbound_date": outbound,
        "return_date": ret,
        "currency": "ILS",
        "hl": "en",
        "api_key": SERPAPI_KEY,
        "adults": 2,
        "type": 1
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
        best = data.get("best_flights", [])
        other = data.get("other_flights", [])
        prices = [f["price"] for f in best + other if "price" in f]
        return min(prices) if prices else None
    except Exception as e:
        print(f"  שגיאה ב-specific: {e}")
        return None

def run():
    print("🔍 מתחיל סריקה...")
    deals = []
    all_pairs = generate_all_valid_pairs()
    print(f"  סה\"כ צירופים תקינים: {len(all_pairs)}")

    # ── חלק 1: SerpAPI explore — כל אירופה ──
    print("\n📡 חלק 1: explore כל אירופה...")
    for month in ["2026-07", "2026-08"]:
        europe_prices = get_price_serpapi_explore_europe(month)
        for destination in ["SOF", "OTP"]:
            price = europe_prices.get(destination)
            if price:
                print(f"  TLV→{destination} {month}: ₪{price}")
                if price < PRICE_THRESHOLD_ILS:
                    msg = (f"✈️ דיל נמצא! (explore)\n"
                           f"TLV → {destination}\n"
                           f"חודש: {month}\n"
                           f"מחיר: ₪{price} לשני נוסעים\n"
                           f"בדוק ב-Skyscanner לפרטים!")
                    deals.append(msg)
                    print(f"  💰 DEAL!")
            else:
                print(f"  TLV→{destination} {month}: לא נמצא מחיר")

    # ── חלק 2: SerpAPI specific — 6 צירופים של היום ──
    print("\n📡 חלק 2: specific תאריכים של היום...")
    todays_pairs = get_todays_pairs(all_pairs)
    for destination in ["SOF", "OTP"]:
        for outbound, ret, nights in todays_pairs:
            outbound_fmt = date.fromisoformat(outbound).strftime("%d/%m/%Y")
            ret_fmt = date.fromisoformat(ret).strftime("%d/%m/%Y")
            print(f"  TLV→{destination} {outbound_fmt}→{ret_fmt} ({nights} לילות)")
            price = get_price_serpapi_specific(destination, outbound, ret)
            if price:
                print(f"  מחיר: ₪{price}")
                if price < PRICE_THRESHOLD_ILS:
                    msg = (f"✈️ דיל נמצא!\n"
                           f"TLV → {destination}\n"
                           f"יציאה: {outbound_fmt} | חזרה: {ret_fmt}\n"
                           f"{nights} לילות\n"
                           f"מחיר: ₪{price} לשני נוסעים")
                    deals.append(msg)
                    print(f"  💰 DEAL!")
            else:
                print(f"  לא נמצא מחיר")

    # ── שליחת תוצאות ──
    if deals:
        for deal in deals:
            send_telegram(deal)
    else:
        send_telegram(f"🔍 סריקה הושלמה — לא נמצאו טיסות מתחת ל-₪{PRICE_THRESHOLD_ILS}")
        print("\nלא נמצאו דילים.")

run()
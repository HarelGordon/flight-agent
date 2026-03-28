import os
import requests
from dotenv import load_dotenv
from datetime import date, timedelta
from fast_flights import FlightData, Passengers, get_flights

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ── הגדרות ──────────────────────────────────
DESTINATIONS = ["SOF", "OTP"]
PRICE_THRESHOLD_ILS = 1400  # שקלים לשני נוסעים — שנה לפי הרצון שלך
START_DATE = date(2026, 7, 12)
END_DATE = date(2026, 8, 9)
# ────────────────────────────────────────────

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def generate_date_pairs(nights_list):
    pairs = []
    current = START_DATE
    while current <= END_DATE:
        for nights in nights_list:
            ret = current + timedelta(days=nights)
            pairs.append((str(current), str(ret), nights))
        current += timedelta(days=1)
    return pairs

def get_price_fast_flights(outbound, return_date, destination):
    try:
        result = get_flights(
            flight_data=[
                FlightData(date=outbound, from_airport="TLV", to_airport=destination),
                FlightData(date=return_date, from_airport=destination, to_airport="TLV"),
            ],
            trip="round-trip",
            seat="economy",
            passengers=Passengers(adults=2, children=0, infants_in_seat=0, infants_on_lap=0),
            fetch_mode="force-fallback",
        )
        valid_prices = []
        for flight in result.flights:
            price_str = (flight.price or "").replace("₪", "").replace(",", "").replace(" ", "").strip()
            try:
                valid_prices.append(int(float(price_str)))
            except:
                continue
        return min(valid_prices) if valid_prices else None
    except Exception as e:
        print(f"    שגיאה ב-fast-flights: {e}")
        return None

def get_price_serpapi_specific(destination, outbound, ret, nights):
    """חיפוש SerpAPI אמין לתאריכים ספציפיים"""
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
        "type": 1  # round trip
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
        best = data.get("best_flights", [])
        other = data.get("other_flights", [])
        prices = [f["price"] for f in best + other if "price" in f]
        return min(prices) if prices else None
    except Exception as e:
        print(f"    שגיאה ב-SerpAPI specific: {e}")
        return None

def get_price_serpapi_explore(destination, month):
    """שאילתת explore — מחזירה הכי זול לחודש שלם, 6 לילות"""
    params = {
        "engine": "google_travel_explore",
        "departure_id": "TLV",
        "arrival_id": destination,
        "travel_month": month,  # "2026-07" או "2026-08"
        "duration": 2,  # 2 = שבוע (6-7 לילות)
        "currency": "ILS",
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
        results = data.get("results", [])
        prices = [r["price"] for r in results if "price" in r]
        return min(prices) if prices else None
    except Exception as e:
        print(f"    שגיאה ב-SerpAPI: {e}")
        return None

def run():
    print("🔍 מתחיל סריקה מלאה...")
    deals = []

    # ── חלק 1: fast-flights — 5 ו-7 לילות ──
    print("\n📡 fast-flights: סורק 5 ו-7 לילות...")
    date_pairs = generate_date_pairs([5, 7])
    for destination in DESTINATIONS:
        for outbound, ret, nights in date_pairs:
            outbound_fmt = date.fromisoformat(outbound).strftime("%d/%m/%Y")
            ret_fmt = date.fromisoformat(ret).strftime("%d/%m/%Y")
            print(f"  TLV→{destination} {outbound_fmt}→{ret_fmt} ({nights} לילות)")
            price = get_price_fast_flights(outbound, ret, destination)
            if price and price < PRICE_THRESHOLD_ILS:
                msg = (f"✈️ דיל נמצא!\n"
                       f"TLV → {destination}\n"
                       f"יציאה: {outbound_fmt} | חזרה: {ret_fmt}\n"
                       f"{nights} לילות\n"
                       f"מחיר: ₪{price} לשני נוסעים")
                deals.append(msg)
                print(f"  💰 DEAL: ₪{price}")

    # ── חלק 2: SerpAPI explore — 6 לילות ──
    print("\n📡 SerpAPI: סורק 6 לילות (explore)...")
    for destination in DESTINATIONS:
        for month in ["2026-07", "2026-08"]:
            print(f"  TLV→{destination} חודש {month} (6 לילות)")
            price = get_price_serpapi_explore(destination, month)
            if price and price < PRICE_THRESHOLD_ILS:
                msg = (f"✈️ דיל נמצא! (6 לילות)\n"
                       f"TLV → {destination}\n"
                       f"חודש: {month}\n"
                       f"מחיר: ₪{price} לשני נוסעים\n"
                       f"בדוק ב-Skyscanner לפרטים!")
                deals.append(msg)
                print(f"  💰 DEAL: ₪{price}")

    # ── חלק 3: SerpAPI ספציפי — 5 ו-7 לילות, תאריכים נבחרים ביולי ──
    print("\n📡 SerpAPI: סורק 5 ו-7 לילות בתאריכים נבחרים...")
    # בוחרים 3 תאריכים מייצגים ביולי — תחילה, אמצע, סוף
    sample_dates = ["2026-07-12", "2026-07-19", "2026-07-26"]
    for destination in DESTINATIONS:
        for start in sample_dates:
            for nights in [5, 7]:
                ret = str(date.fromisoformat(start) + timedelta(days=nights))
                outbound_fmt = date.fromisoformat(start).strftime("%d/%m/%Y")
                ret_fmt = date.fromisoformat(ret).strftime("%d/%m/%Y")
                print(f"  TLV→{destination} {outbound_fmt}→{ret_fmt} ({nights} לילות) [SerpAPI]")
                price = get_price_serpapi_specific(destination, start, ret, nights)
                if price and price < PRICE_THRESHOLD_ILS:
                    msg = (f"✈️ דיל נמצא! [SerpAPI מאומת]\n"
                        f"TLV → {destination}\n"
                        f"יציאה: {outbound_fmt} | חזרה: {ret_fmt}\n"
                        f"{nights} לילות\n"
                        f"מחיר: ₪{price} לשני נוסעים")
                    deals.append(msg)
                    print(f"  💰 DEAL: ₪{price}")

    # ── שליחת תוצאות ──
    if deals:
        for deal in deals:
            send_telegram(deal)
    else:
        send_telegram(f"🔍 סריקה הושלמה — לא נמצאו טיסות מתחת ל-₪{PRICE_THRESHOLD_ILS}")
        print("\nלא נמצאו דילים הפעם.")

run()
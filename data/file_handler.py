# file_handler.py - File handling for customers, orders, feedback

import os
import json
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
BILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bills")

CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.txt")
ORDERS_FILE    = os.path.join(DATA_DIR, "orders.txt")
FEEDBACK_FILE  = os.path.join(DATA_DIR, "feedback.txt")
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.txt")

def _ensure_files():
    os.makedirs(DATA_DIR,  exist_ok=True)
    os.makedirs(BILLS_DIR, exist_ok=True)
    for f in [CUSTOMERS_FILE, ORDERS_FILE, FEEDBACK_FILE, FAVORITES_FILE]:
        if not os.path.exists(f):
            open(f, "w").close()

_ensure_files()


# ---------- Customers ----------

def save_customer(name: str, phone: str, email: str = ""):
    with open(CUSTOMERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{name}|{phone}|{email}|{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

def load_customers() -> list:
    customers = []
    if not os.path.exists(CUSTOMERS_FILE):
        return customers
    with open(CUSTOMERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split("|")
                if len(parts) >= 2:
                    customers.append({
                        "name":  parts[0],
                        "phone": parts[1],
                        "email": parts[2] if len(parts) > 2 else "",
                        "date":  parts[3] if len(parts) > 3 else "",
                    })
    return customers


# ---------- Orders ----------

def save_order(order_data: dict):
    with open(ORDERS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(order_data, ensure_ascii=False) + "\n")

def load_orders() -> list:
    orders = []
    if not os.path.exists(ORDERS_FILE):
        return orders
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    orders.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return orders

def search_orders(query: str) -> list:
    query = query.lower()
    return [o for o in load_orders()
            if query in o.get("customer_name", "").lower()
            or query in o.get("phone", "").lower()]

def get_next_invoice_number() -> str:
    orders = load_orders()
    return f"TWT{len(orders) + 1:03d}"


# ---------- Feedback ----------

def save_feedback(name: str, phone: str, rating: int, comment: str):
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        entry = {
            "name": name, "phone": phone,
            "rating": rating, "comment": comment,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def load_feedback() -> list:
    feedbacks = []
    if not os.path.exists(FEEDBACK_FILE):
        return feedbacks
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    feedbacks.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return feedbacks


# ---------- Favorites ----------

def load_favorites() -> list:
    if not os.path.exists(FAVORITES_FILE):
        return []
    with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return []
    return []

def save_favorites(item_ids: list):
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(item_ids))

def toggle_favorite(item_id: str) -> bool:
    favs = load_favorites()
    if item_id in favs:
        favs.remove(item_id)
        added = False
    else:
        favs.append(item_id)
        added = True
    save_favorites(favs)
    return added

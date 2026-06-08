"""
image_loader.py - Food image downloader for TWIN T Restaurant.
Uses Pexels API to search and download the correct dish photo for each item.
"""
import os, urllib.request, ssl, json
from typing import Callable, Optional

from PySide6.QtCore import QThread, Signal, Qt, QRect
from PySide6.QtGui  import (QPixmap, QPainter, QColor, QLinearGradient,
                             QRadialGradient, QFont)

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "image_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
LOG_FILE  = os.path.join(BASE_DIR, "image_loader.log")

# ── Pexels API key ────────────────────────────────────────────────────────────
PEXELS_API_KEY = "oHNjyLjZ0UA4BbSV8LIRU6D722IHVfyM2l2PTX2MBDbcTSgzwBSk2hxb"

def _log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

# ── Dish → best Pexels search query (very specific for correct image) ─────────
DISH_QUERIES = {
    # Soups Veg
    "SV001": "tomato basil soup bowl",
    "SV002": "hot sour vegetable soup",
    "SV003": "manchow soup noodles",
    "SV004": "sweet corn soup",
    "SV005": "lemon coriander soup",
    "SV006": "ginger broth soup bowl",
    # Soups Non-Veg
    "SN001": "chicken hot sour soup",
    "SN002": "chicken manchow soup",
    "SN003": "chicken sweet corn soup",
    "SN004": "indian chicken shorba",
    "SN005": "saffron chicken soup",
    # Salads
    "SA001": "fresh green salad bowl",
    "SA002": "sprouts salad healthy",
    "SA003": "lettuce salad fresh",
    "SA004": "russian salad mayonnaise",
    # Fries & Snacks
    "FS001": "french fries crispy golden",
    "FS002": "spicy peri peri fries",
    "FS003": "cheese fries loaded",
    "FS004": "chicken loaded fries",
    "FS005": "garlic bread toasted",
    "FS006": "cheese garlic bread melted",
    # South Indian Starters
    "SI001": "andhra chicken pakoda fried",
    "SI002": "kodi vepudu andhra chicken fry",
    "SI003": "spicy andhra chicken fry dry",
    "SI004": "green chilli chicken fry andhra",
    "SI005": "andhra fried fish spicy",
    "SI006": "prawns fry indian spicy",
    # Tandoor Specials
    "TS001": "chicken tikka skewer charred",
    "TS002": "murgh kebab garlic tandoor",
    "TS003": "achari chicken tikka pickle",
    "TS004": "malai chicken kebab creamy",
    "TS005": "tangdi kebab chicken leg",
    "TS006": "tandoori chicken half grilled",
    "TS007": "tandoori chicken whole grilled",
    "TS008": "fish tikka grilled skewer",
    "TS009": "tandoori prawns grilled",
    # Chinese Starters
    "CS001": "egg chilli stir fry indian chinese",
    "CS002": "egg manchurian balls sauce",
    "CS003": "chicken manchurian dark sauce",
    "CS004": "chicken chilli dry indo chinese",
    "CS005": "chicken 65 crispy fried red",
    "CS006": "shangrila chicken saucy",
    "CS007": "spicy dragon chicken chinese",
    "CS008": "black pepper chicken dry",
    "CS009": "chicken lollipop fried",
    "CS010": "chicken wings crispy fried",
    "CS011": "crunchy fried chicken golden",
    "CS012": "chicken majestic dry spiced",
    "CS013": "fish chilli stir fry",
    "CS014": "apollo fish fry spicy",
    "CS015": "butter garlic fish fry",
    "CS016": "stir fried prawns spicy",
    "CS017": "golden fried prawns crispy",
    # Biryanis
    "BR001": "chicken dum biryani layered",
    "BR002": "chicken fry piece biryani",
    "BR003": "chicken boneless biryani",
    "BR004": "chicken special biryani pot",
    "BR005": "mutton biryani indian",
    "BR006": "mutton special biryani",
    "BR007": "prawn biryani seafood",
    "BR008": "fish biryani indian",
    "BR009": "egg biryani rice",
    "BR010": "vegetable biryani veg",
    "BR011": "paneer biryani vegetarian",
    "BR012": "family biryani large pot",
    # Main Course
    "MC001": "butter chicken creamy orange gravy",
    "MC002": "kadai chicken wok spicy",
    "MC003": "chicken curry indian brown gravy",
    "MC004": "mutton curry indian dark gravy",
    "MC005": "paneer butter masala orange gravy",
    "MC006": "kadai paneer wok",
    "MC007": "vegetable kurma coconut gravy",
    "MC008": "dal tadka yellow lentil",
    # Indian Breads
    "IB001": "butter naan bread indian",
    "IB002": "garlic naan bread",
    "IB003": "butter roti indian flatbread",
    "IB004": "tandoori roti flatbread",
    "IB005": "kulcha stuffed bread",
    # Noodles
    "NO001": "vegetable noodles stir fry",
    "NO002": "egg noodles stir fry",
    "NO003": "chicken noodles chinese",
    "NO004": "mixed noodles",
    "NO005": "schezwan noodles spicy red",
    # Fried Rice
    "FR001": "vegetable fried rice wok",
    "FR002": "egg fried rice",
    "FR003": "chicken fried rice",
    "FR004": "schezwan fried rice spicy",
    "FR005": "mixed fried rice",
    # Desserts
    "DE001": "chocolate brownie dessert",
    "DE002": "brownie with ice cream scoop",
    "DE003": "vanilla ice cream scoop white",
    "DE004": "chocolate ice cream dark",
    "DE005": "gulab jamun indian sweet syrup",
    "DE006": "double ka meetha bread dessert indian",
    # Beverages
    "BV001": "coca cola glass ice",
    "BV002": "pepsi cold drink glass",
    "BV003": "sprite lemon soda glass",
    "BV004": "fresh lime soda glass",
    "BV005": "mineral water glass bottle",
    "BV006": "mango milkshake yellow glass",
    "BV007": "chocolate milkshake glass",
    "BV008": "oreo milkshake cookie",
    "BV009": "iced cold coffee glass",
}

CATEGORY_GRADIENTS = {
    "Soups (Veg)":           ("#FF6B35","#F7931E"),
    "Soups (Non-Veg)":       ("#C0392B","#E74C3C"),
    "Salads":                ("#27AE60","#2ECC71"),
    "Fries & Snacks":        ("#F39C12","#F1C40F"),
    "South Indian Starters": ("#E74C3C","#C0392B"),
    "Tandoor Specials":      ("#922B21","#E74C3C"),
    "Chinese Starters":      ("#D35400","#E67E22"),
    "Biryanis":              ("#8E6B3E","#C8A96A"),
    "Main Course":           ("#1A5276","#2980B9"),
    "Indian Breads":         ("#D4AC0D","#F4D03F"),
    "Noodles":               ("#D35400","#E59866"),
    "Fried Rice":            ("#B7950B","#F1C40F"),
    "Desserts":              ("#76448A","#A569BD"),
    "Beverages":             ("#1ABC9C","#48C9B0"),
}
CATEGORY_EMOJI = {
    "Soups (Veg)":"🍲","Soups (Non-Veg)":"🥣","Salads":"🥗",
    "Fries & Snacks":"🍟","South Indian Starters":"🍗","Tandoor Specials":"🔥",
    "Chinese Starters":"🥡","Biryanis":"🍛","Main Course":"🍲",
    "Indian Breads":"🫓","Noodles":"🍜","Fried Rice":"🍚",
    "Desserts":"🍰","Beverages":"🥤",
}

def _cache_path(item_id, w, h):
    return os.path.join(CACHE_DIR, f"{item_id}_{w}x{h}.jpg")

def _is_valid_image(data: bytes) -> bool:
    if len(data) < 4000: return False
    if data[:3] == b'\xff\xd8\xff': return True
    if data[:8] == b'\x89PNG\r\n\x1a\n': return True
    if data[8:12] == b'WEBP': return True
    return False

def _load_from_disk(item_id, w, h) -> Optional[QPixmap]:
    path = _cache_path(item_id, w, h)
    if os.path.exists(path) and os.path.getsize(path) > 3000:
        px = QPixmap(path)
        if not px.isNull():
            return px.scaled(w, h, Qt.KeepAspectRatioByExpanding,
                             Qt.SmoothTransformation).copy(0, 0, w, h)
    return None

def _make_gradient_pixmap(category: str, w: int, h: int) -> QPixmap:
    px = QPixmap(w, h); px.fill(Qt.transparent)
    p = QPainter(px); p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, w, h)
    c1, c2 = CATEGORY_GRADIENTS.get(category, ("#C0392B","#E74C3C"))
    g.setColorAt(0.0, QColor(c1)); g.setColorAt(1.0, QColor(c2))
    p.setBrush(g); p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, w, h, 12, 12)
    rg = QRadialGradient(w*0.25, h*0.25, w*0.6)
    rg.setColorAt(0.0, QColor(255,255,255,50))
    rg.setColorAt(1.0, QColor(255,255,255,0))
    p.setBrush(rg); p.drawRoundedRect(0, 0, w, h, 12, 12)
    p.setFont(QFont("Segoe UI Emoji", h//3))
    p.setPen(QColor(255,255,255,220))
    p.drawText(QRect(0,0,w,h), Qt.AlignCenter, CATEGORY_EMOJI.get(category,"🍽️"))
    p.end()
    return px

def _search_pexels(query: str, w: int, h: int) -> Optional[bytes]:
    """Search Pexels API and return image bytes for best match."""
    ctx = ssl.create_default_context()
    api_url = (
        f"https://api.pexels.com/v1/search"
        f"?query={urllib.parse.quote(query)}&per_page=1&size=medium"
        f"&orientation=landscape"
    )
    headers = {
        "Authorization": PEXELS_API_KEY,
        "User-Agent": "TwinT-Restaurant/1.0",
    }
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
            result = json.loads(r.read())
        photos = result.get("photos", [])
        if not photos:
            _log(f"  No results for: {query}")
            return None
        # Download the actual image
        img_url = photos[0]["src"]["medium"]
        img_req = urllib.request.Request(img_url, headers={
            "User-Agent": "TwinT-Restaurant/1.0",
        })
        with urllib.request.urlopen(img_req, timeout=12, context=ctx) as r:
            data = r.read()
        return data if _is_valid_image(data) else None
    except Exception as e:
        _log(f"  Pexels search error '{query}': {e}")
        return None

# lazy import for url encoding
import urllib.parse

class _DownloadWorker(QThread):
    finished = Signal(str, object)

    def __init__(self, item_id, item_name, category, w, h):
        super().__init__()
        self.item_id   = item_id
        self.item_name = item_name
        self.category  = category
        self.w, self.h = w, h

    def run(self):
        dest  = _cache_path(self.item_id, self.w, self.h)
        query = DISH_QUERIES.get(self.item_id, self.item_name + " food dish")
        _log(f"Searching: '{self.item_name}' → query='{query}'")

        data = _search_pexels(query, self.w, self.h)
        if data:
            with open(dest, "wb") as f:
                f.write(data)
            _log(f"  ✓ saved {len(data)//1024}KB for {self.item_id}")
        else:
            _log(f"  ✗ no image found for {self.item_id}")

        px = _load_from_disk(self.item_id, self.w, self.h)
        if px is None:
            px = _make_gradient_pixmap(self.category, self.w, self.h)
        self.finished.emit(self.item_id, px)

_active_workers: list = []

def get_food_pixmap(item_name: str, item_id: str, category: str,
                    size=(210,140), callback: Optional[Callable]=None) -> QPixmap:
    w, h = size
    cached = _load_from_disk(item_id, w, h)
    if cached:
        return cached
    placeholder = _make_gradient_pixmap(category, w, h)
    if callback:
        worker = _DownloadWorker(item_id, item_name, category, w, h)
        def _done(iid, px, wk=worker):
            if iid == item_id: callback(px)
            try: _active_workers.remove(wk)
            except ValueError: pass
        worker.finished.connect(_done)
        _active_workers.append(worker)
        worker.start()
    return placeholder

def preload_images(items: list, category: str="", size=(210,140)):
    w, h = size
    for item in items:
        iid = item.get("id","")
        if not _load_from_disk(iid, w, h):
            worker = _DownloadWorker(iid, item.get("name",""), category, w, h)
            def _cleanup(_, px, wk=worker):
                try: _active_workers.remove(wk)
                except ValueError: pass
            worker.finished.connect(_cleanup)
            _active_workers.append(worker)
            worker.start()

def clear_cache():
    """Delete all cached images to force fresh download."""
    removed = 0
    for f in os.listdir(CACHE_DIR):
        fp = os.path.join(CACHE_DIR, f)
        try:
            os.remove(fp)
            removed += 1
        except Exception:
            pass
    _log(f"Cache cleared: {removed} files removed")
    return removed

if __name__ == "__main__":
    print(f"Cache cleared: {clear_cache()} files")
    print(f"Total dish queries: {len(DISH_QUERIES)}")
    print("Now run main.py — images will download automatically!")

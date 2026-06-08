"""
TWIN T Restaurant – Smart Self-Ordering System
Main application entry point and all GUI screens.
"""

import sys
import os
import random
from datetime import datetime

# ── path setup ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "data"))

from menu_data    import MENU_DATA, CATEGORY_ICONS, RECOMMENDATIONS, TODAY_SPECIAL
from file_handler import (save_customer, load_customers, save_order, load_orders,
                          search_orders, get_next_invoice_number, save_feedback,
                          load_feedback, load_favorites, toggle_favorite)
from pdf_generator import generate_pdf_bill
from image_loader  import get_food_pixmap, preload_images

# ── PySide6 ───────────────────────────────────────────────────────────────────
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QTextEdit, QDialog,
    QProgressBar, QStackedWidget, QComboBox, QSpinBox, QMessageBox,
    QSizePolicy, QButtonGroup, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QSlider, QCheckBox, QSpacerItem,
)
from PySide6.QtCore  import (Qt, QTimer, QPropertyAnimation, QEasingCurve,
                              Signal, QThread, QSize, QRect, QPoint)
from PySide6.QtGui   import (QFont, QColor, QPalette, QPixmap, QPainter,
                              QLinearGradient, QRadialGradient, QBrush, QPen, QIcon,
                              QFontDatabase, QCursor, QGuiApplication)

# ══════════════════════════════════════════════════════════════════════════════
#  Theme / palette
# ══════════════════════════════════════════════════════════════════════════════
#  Single Royal Crimson & Gold theme
# ══════════════════════════════════════════════════════════════════════════════
theme = {
    "bg":        "#1A0303", "card":    "#2A0808", "primary":  "#D4AC0D",
    "primary2":  "#F5D060", "accent":  "#D4AC0D", "text":     "#F5E6C8",
    "text2":     "#C4A882", "border":  "#5C3A1A", "success":  "#2ECC71",
    "sidebar":   "#0D0101", "sidebar_text": "#D4AC0D",
    "cart_bg":   "#1A0303", "highlight":    "#3B0E0E",
    "dialog":    "#2A0808",
}
favorites_cache: list = []
cart: list            = []
def T(key): return theme[key]
# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════
def make_label(text="", size=12, bold=False, color_key="text",
               align=Qt.AlignLeft, parent=None):
    lbl = QLabel(text, parent)
    f   = QFont("Segoe UI", size)
    f.setBold(bold)
    lbl.setFont(f)
    lbl.setStyleSheet(f"color:{T(color_key)};")
    lbl.setAlignment(align)
    return lbl
def make_btn(text, color=None, text_color="#1A0303", size=11, parent=None):
    btn = QPushButton(text, parent)
    c   = color or T("primary")
    btn.setStyleSheet(f"""
        QPushButton {{
            background:{c}; color:{text_color};
            border-radius:8px; padding:8px 16px;
            font-size:{size}px; font-weight:bold;
        }}
        QPushButton:hover   {{ background:{T("primary2")}; color:#1A0303; }}
        QPushButton:pressed {{ background:{T("accent")};   color:#1A0303; }}
    """)
    btn.setCursor(QCursor(Qt.PointingHandCursor))
    return btn


def emoji_pixmap(emoji: str, size: int = 64) -> QPixmap:
    """Render an emoji as a pixmap (fallback food image)."""
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p  = QPainter(px)
    f  = QFont("Segoe UI Emoji", size // 2)
    p.setFont(f)
    p.drawText(QRect(0, 0, size, size), Qt.AlignCenter, emoji)
    p.end()
    return px


CATEGORY_EMOJI = {
    "Soups (Veg)": "🍲",       "Soups (Non-Veg)": "🥣",
    "Salads": "🥗",             "Fries & Snacks": "🍟",
    "South Indian Starters":"🍗","Tandoor Specials":"🔥",
    "Chinese Starters":"🥡",    "Biryanis":"🍛",
    "Main Course":"🍲",         "Indian Breads":"🫓",
    "Noodles":"🍜",             "Fried Rice":"🍚",
    "Desserts":"🍰",            "Beverages":"🥤",
}


# ══════════════════════════════════════════════════════════════════════════════
#  Cart helpers
# ══════════════════════════════════════════════════════════════════════════════
def cart_add(item: dict):
    for ci in cart:
        if ci["id"] == item["id"]:
            ci["quantity"] += 1
            return
    cart.append({**item, "quantity": 1})


def cart_remove(item_id: str):
    global cart
    cart = [ci for ci in cart if ci["id"] != item_id]


def cart_subtotal() -> float:
    return sum(ci["price"] * ci["quantity"] for ci in cart)


def calc_totals(subtotal: float):
    discount = subtotal * 0.10 if subtotal > 2000 else 0.0
    taxable  = subtotal - discount
    gst      = taxable * 0.05
    final    = taxable + gst
    specials = []
    if subtotal > 5000:
        specials.append("Fresh Lime Soda")
    if subtotal > 8000:
        specials.append("Complimentary Dessert")
    return discount, gst, final, specials


# ══════════════════════════════════════════════════════════════════════════════
#  Notification toast
# ══════════════════════════════════════════════════════════════════════════════
class Toast(QLabel):
    def __init__(self, msg: str, parent=None):
        super().__init__(msg, parent)
        self.setStyleSheet(f"""
            background:{T("success")}; color:#fff;
            border-radius:10px; padding:10px 20px;
            font-size:12px; font-weight:bold;
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.adjustSize()
        if parent:
            gp = parent.mapToGlobal(QPoint(0, 0))
            self.move(gp.x() + parent.width()//2 - self.width()//2,
                      gp.y() + parent.height() - 80)
        self.show()
        QTimer.singleShot(2200, self.close)


# ══════════════════════════════════════════════════════════════════════════════
#  Particle  (floating gold sparkle)
# ══════════════════════════════════════════════════════════════════════════════
class _Particle:
    def __init__(self, w, h):
        self.reset(w, h)

    def reset(self, w, h):
        self.x  = random.uniform(0, w)
        self.y  = random.uniform(0, h)
        self.r  = random.uniform(1.5, 4.0)
        self.vx = random.uniform(-0.4, 0.4)
        self.vy = random.uniform(-0.8, -0.2)
        self.alpha = random.uniform(80, 200)
        self.fade  = random.uniform(0.4, 1.2)

    def step(self, w, h):
        self.x    += self.vx
        self.y    += self.vy
        self.alpha -= self.fade
        if self.alpha <= 0 or self.y < -10:
            self.reset(w, h)
            self.y = h + 5


# ══════════════════════════════════════════════════════════════════════════════
#  Crown + Name Centre Widget  (no ring)
# ══════════════════════════════════════════════════════════════════════════════
class _CrownWidget(QWidget):
    """Crown emoji + TwinT name, colours follow portal theme."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(2)
        lay.setContentsMargins(20, 10, 20, 10)

        self._crown_lbl = QLabel("👑")
        self._crown_lbl.setFont(QFont("Segoe UI Emoji", 96))
        self._crown_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._crown_lbl)

        self._name_lbl = QLabel("TwinT")
        self._name_lbl.setFont(QFont("Georgia", 52, QFont.Bold))
        self._name_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._name_lbl)

        self.set_theme(PORTAL_THEMES[SELECTED_PORTAL_THEME])

    def set_theme(self, pt: dict):
        c = pt["tag_color"]
        self._name_lbl.setStyleSheet(f"color:{c}; letter-spacing:5px;")


# ══════════════════════════════════════════════════════════════════════════════
#  Welcome Portal  (replaces old SplashScreen)
# ══════════════════════════════════════════════════════════════════════════════
class SplashScreen(QWidget):
    """
    Full-screen royal welcome portal.
    Shows the TwinT logo, animated gold particles, and an
    'Enter Restaurant' button.  Emits done() when button is clicked.
    """
    done = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # Start full-screen
        screen_geo = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)

        self._particles = [_Particle(screen_geo.width(), screen_geo.height())
                           for _ in range(60)]
        self._anim_val  = 0      # 0→100 for fade-in
        self._glow_val  = 0      # oscillating glow
        self._glow_dir  = 1

        self._build_ui()

        # Particle + glow animation timer
        self._ptimer = QTimer(self)
        self._ptimer.timeout.connect(self._tick)
        self._ptimer.start(16)   # ~60 fps

    # ── build ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Use absolute layout so theme buttons can sit top-right
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)

        # ── Outer container (fills screen) ────────────────────────────────
        outer = QWidget(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("background:transparent;")
        self._outer = outer

        # Centre column
        col = QVBoxLayout(outer)
        col.setAlignment(Qt.AlignCenter)
        col.setSpacing(0)
        col.setContentsMargins(0, 0, 0, 0)

        col.addStretch(1)

        # ── Logo image ────────────────────────────────────────────────────
        self._logo_lbl = QLabel()
        self._logo_lbl.setAlignment(Qt.AlignCenter)
        logo_path = os.path.join(BASE_DIR, "logo.png")
        if os.path.exists(logo_path):
            px = QPixmap(logo_path).scaled(
                360, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._logo_lbl.setPixmap(px)
        else:
            self._logo_lbl.setText("👑")
            self._logo_lbl.setFont(QFont("Segoe UI Emoji", 90))
        col.addWidget(self._logo_lbl, 0, Qt.AlignCenter)

        col.addSpacing(18)

        # ── Tagline ───────────────────────────────────────────────────────
        self.tag_lbl = QLabel("✦   Welcome to TwinT Restaurant   ✦")
        self.tag_lbl.setFont(QFont("Georgia", 17, QFont.Bold))
        self.tag_lbl.setAlignment(Qt.AlignCenter)
        col.addWidget(self.tag_lbl)

        col.addSpacing(6)

        sub = QLabel("Taste Beyond Expectations")
        sub.setFont(QFont("Georgia", 11))
        sub.setAlignment(Qt.AlignCenter)
        self._sub_lbl = sub
        col.addWidget(sub)

        col.addSpacing(36)

        # ── Enter button ──────────────────────────────────────────────────
        self.enter_btn = QPushButton("  ✦  Enter Restaurant  ✦  ")
        self.enter_btn.setFixedSize(320, 58)
        self.enter_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.enter_btn.clicked.connect(self._on_enter)
        col.addWidget(self.enter_btn, 0, Qt.AlignCenter)

        col.addSpacing(20)

        btm = QLabel("Est. 2024  •  Fine Dining & Takeaway")
        btm.setFont(QFont("Georgia", 9))
        btm.setAlignment(Qt.AlignCenter)
        self._btm_lbl = btm
        col.addWidget(btm)

        col.addStretch(1)

        self.layout().addWidget(outer)

        # Apply fixed gold styling
        self.tag_lbl.setStyleSheet("color:#D4AC0D; letter-spacing:2px;")
        self._sub_lbl.setStyleSheet("color:rgba(212,172,13,170);")
        self._btm_lbl.setStyleSheet("color:rgba(212,172,13,100);")
        self.enter_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #7A5C10, stop:0.5 #D4AC0D, stop:1 #7A5C10);
                color: #1A0505; border: 2px solid #F5D060;
                border-radius: 29px; font-size: 15px; font-weight: bold;
                font-family: Georgia; letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #D4AC0D, stop:0.5 #F5D060, stop:1 #D4AC0D);
                border: 2px solid #fff8dc;
            }
            QPushButton:pressed { background: #7A5C10; }
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_outer"):
            self._outer.setGeometry(0, 0, self.width(), self.height())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Deep crimson background
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor("#0D0101"))
        bg.setColorAt(0.4, QColor("#1A0303"))
        bg.setColorAt(1.0, QColor("#2A0505"))
        p.fillRect(0, 0, w, h, bg)

        # Centre glow
        glow_r = int(300 + self._glow_val * 40)
        rg = QRadialGradient(w / 2, h / 2, glow_r)
        rg.setColorAt(0.0, QColor(140, 50, 10, 60))
        rg.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(rg); p.setPen(Qt.NoPen)
        p.drawEllipse(int(w/2 - glow_r), int(h/2 - glow_r), glow_r*2, glow_r*2)

        # Gold particles
        for par in self._particles:
            c = QColor(212, 172, 13, int(par.alpha))
            p.setBrush(c); p.setPen(Qt.NoPen)
            p.drawEllipse(int(par.x - par.r), int(par.y - par.r),
                          int(par.r * 2), int(par.r * 2))

        # Gold border
        p.setPen(QPen(QColor(120, 90, 5, 120), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRect(8, 8, w - 16, h - 16)
        p.end()

    # ── Animation tick ──────────────────────────────────────────────────────
    def _tick(self):
        w, h = self.width(), self.height()
        for pt in self._particles:
            pt.step(w, h)

        self._glow_val += 0.02 * self._glow_dir
        if self._glow_val >= 1.0:
            self._glow_dir = -1
        elif self._glow_val <= 0.0:
            self._glow_dir = 1

        self.update()

    # ── Enter clicked ───────────────────────────────────────────────────────
    def _on_enter(self):
        self._ptimer.stop()
        self.done.emit()


# ══════════════════════════════════════════════════════════════════════════════
#  Food Card Widget
# ══════════════════════════════════════════════════════════════════════════════
class FoodCard(QFrame):
    add_to_cart = Signal(dict)
    toggle_fav  = Signal(str)

    # Image area dimensions
    IMG_W, IMG_H = 210, 140

    def __init__(self, item: dict, category: str, parent=None):
        super().__init__(parent)
        self.item     = item
        self.category = category
        self._build()

    def _build(self):
        self.setFixedSize(210, 310)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            FoodCard {{
                background:{T("card")}; border-radius:14px;
                border:1px solid {T("border")};
            }}
            FoodCard:hover {{ border:2px solid {T("primary")}; }}
        """)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 10)
        root.setSpacing(0)

        # ── image container (top, rounded top corners) ─────────
        self.img_lbl = QLabel()
        self.img_lbl.setFixedSize(self.IMG_W, self.IMG_H)
        self.img_lbl.setAlignment(Qt.AlignCenter)
        self.img_lbl.setStyleSheet("""
            QLabel {
                border-top-left-radius:14px;
                border-top-right-radius:14px;
                border-bottom-left-radius:0px;
                border-bottom-right-radius:0px;
            }
        """)

        # Start with gradient placeholder, swap when image loads
        px = get_food_pixmap(
            self.item["name"], self.item["id"], self.category,
            size=(self.IMG_W, self.IMG_H),
            callback=self._on_image_loaded,
        )
        self.img_lbl.setPixmap(px)
        root.addWidget(self.img_lbl)

        # ── fav + veg badge row (overlaid feel via layout) ─────
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(8, 6, 8, 2)

        veg_lbl = QLabel("🟢 Veg" if self.item["veg"] else "🔴 Non-Veg")
        veg_lbl.setFont(QFont("Segoe UI", 7, QFont.Bold))
        veg_color = "#27AE60" if self.item["veg"] else "#E74C3C"
        veg_lbl.setStyleSheet(f"""
            background:{veg_color}22; color:{veg_color};
            border:1px solid {veg_color}55;
            border-radius:4px; padding:1px 5px;
        """)
        badge_row.addWidget(veg_lbl)
        badge_row.addStretch()

        fav_id = self.item["id"]
        self.fav_btn = QPushButton("♡")
        self.fav_btn.setFixedSize(28, 28)
        self.fav_btn.setCheckable(True)
        self.fav_btn.setChecked(fav_id in load_favorites())
        self._update_fav_style()
        self.fav_btn.clicked.connect(lambda: self.toggle_fav.emit(fav_id))
        self.fav_btn.clicked.connect(self._update_fav_style)
        badge_row.addWidget(self.fav_btn)
        root.addLayout(badge_row)

        # ── name ───────────────────────────────────────────────
        inner = QVBoxLayout()
        inner.setContentsMargins(10, 0, 10, 0)
        inner.setSpacing(3)

        name_lbl = QLabel(self.item["name"])
        name_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        name_lbl.setStyleSheet(f"color:{T('text')};")
        name_lbl.setWordWrap(True)
        name_lbl.setFixedHeight(36)
        inner.addWidget(name_lbl)

        # ── desc ───────────────────────────────────────────────
        desc_lbl = QLabel(self.item.get("desc", ""))
        desc_lbl.setFont(QFont("Segoe UI", 8))
        desc_lbl.setStyleSheet(f"color:{T('text2')};")
        desc_lbl.setWordWrap(True)
        desc_lbl.setFixedHeight(28)
        inner.addWidget(desc_lbl)

        # ── rating + time ──────────────────────────────────────
        meta_row = QHBoxLayout()
        rat_lbl  = QLabel(f"⭐ {self.item['rating']}")
        rat_lbl.setFont(QFont("Segoe UI", 8))
        rat_lbl.setStyleSheet(f"color:{T('accent')};")
        time_lbl = QLabel(f"⏱ {self.item['prep_time']} min")
        time_lbl.setFont(QFont("Segoe UI", 8))
        time_lbl.setStyleSheet(f"color:{T('text2')};")
        meta_row.addWidget(rat_lbl)
        meta_row.addStretch()
        meta_row.addWidget(time_lbl)
        inner.addLayout(meta_row)

        # ── price + add button ─────────────────────────────────
        bot_row = QHBoxLayout()
        price_lbl = QLabel(f"₹{self.item['price']}")
        price_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        price_lbl.setStyleSheet(f"color:{T('primary')};")
        bot_row.addWidget(price_lbl)
        bot_row.addStretch()
        add_btn = QPushButton("+ Add")
        add_btn.setFixedSize(72, 30)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background:{T('primary')}; color:#fff;
                border-radius:6px; font-size:10px; font-weight:bold;
            }}
            QPushButton:hover {{ background:{T('primary2')}; }}
        """)
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))
        add_btn.clicked.connect(lambda: self.add_to_cart.emit(self.item))
        bot_row.addWidget(add_btn)
        inner.addLayout(bot_row)

        root.addLayout(inner)

    def _on_image_loaded(self, px: QPixmap):
        """Called from background thread via Qt signal – safe to update UI."""
        self.img_lbl.setPixmap(px)

    def _update_fav_style(self):
        checked = self.fav_btn.isChecked()
        self.fav_btn.setText("❤" if checked else "♡")
        c = "#E74C3C" if checked else T("text2")
        self.fav_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{c};
                font-size:16px; border:none; }}
        """)


# ══════════════════════════════════════════════════════════════════════════════
#  Cart Panel (right sidebar)
# ══════════════════════════════════════════════════════════════════════════════
class CartPanel(QWidget):
    checkout_clicked = Signal()
    updated          = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{T('sidebar')}; border-radius:0px;")
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("🛒  Your Cart")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color:{T('sidebar_text')};")
        root.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{T('border')};")
        root.addWidget(sep)

        # scroll area for cart items
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:transparent; border:none;")
        self.items_widget = QWidget()
        self.items_layout = QVBoxLayout(self.items_widget)
        self.items_layout.setSpacing(6)
        self.items_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.items_widget)
        root.addWidget(self.scroll, 1)

        # totals
        self.lbl_subtotal  = QLabel("Subtotal : ₹0")
        self.lbl_discount  = QLabel("")
        self.lbl_gst       = QLabel("GST (5%) : ₹0")
        self.lbl_total     = QLabel("Total    : ₹0")
        for lbl in [self.lbl_subtotal, self.lbl_discount, self.lbl_gst]:
            lbl.setStyleSheet(f"color:{T('sidebar_text')}; font-size:11px;")
        self.lbl_total.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.lbl_total.setStyleSheet(f"color:{T('accent')};")
        root.addWidget(self.lbl_subtotal)
        root.addWidget(self.lbl_discount)
        root.addWidget(self.lbl_gst)
        root.addWidget(self.lbl_total)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"color:{T('border')};")
        root.addWidget(sep2)

        btn_row = QHBoxLayout()
        clear_btn   = make_btn("🗑 Clear", "#555")
        checkout_btn = make_btn("💳 Checkout", T("primary"))
        clear_btn.clicked.connect(self._clear_cart)
        checkout_btn.clicked.connect(self.checkout_clicked)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(checkout_btn)
        root.addLayout(btn_row)

    def refresh(self):
        # clear items layout
        while self.items_layout.count():
            child = self.items_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not cart:
            empty = QLabel("Your cart is empty.\nAdd items to get started! 🍽️")
            empty.setStyleSheet(f"color:{T('sidebar_text')}; font-size:11px;")
            empty.setAlignment(Qt.AlignCenter)
            empty.setWordWrap(True)
            self.items_layout.addWidget(empty)
        else:
            for ci in cart:
                row = self._make_cart_row(ci)
                self.items_layout.addWidget(row)

        sub = cart_subtotal()
        disc, gst, final, _ = calc_totals(sub)
        self.lbl_subtotal.setText(f"Subtotal : ₹{sub:.0f}")
        if disc:
            self.lbl_discount.setText(f"Discount : -₹{disc:.0f}  🎉")
            self.lbl_discount.setStyleSheet("color:#2ECC71; font-size:11px;")
        else:
            self.lbl_discount.setText("")
        self.lbl_gst.setText(f"GST (5%) : ₹{gst:.2f}")
        self.lbl_total.setText(f"Total    : ₹{final:.2f}")

    def _make_cart_row(self, ci: dict) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{ background:{T("card")}; border-radius:8px;
                border:1px solid {T("border")}; }}
        """)
        row = QHBoxLayout(frame)
        row.setContentsMargins(6, 4, 6, 4)

        name_lbl = QLabel(ci["name"][:22] + ("…" if len(ci["name"]) > 22 else ""))
        name_lbl.setStyleSheet(f"color:{T('text')}; font-size:9px;")
        row.addWidget(name_lbl, 1)

        minus = QPushButton("−")
        minus.setFixedSize(22, 22)
        minus.setStyleSheet(f"background:{T('primary')}; color:#fff; border-radius:4px; font-weight:bold;")
        minus.setCursor(QCursor(Qt.PointingHandCursor))
        minus.clicked.connect(lambda _, c=ci: self._dec(c))

        qty_lbl = QLabel(str(ci["quantity"]))
        qty_lbl.setFixedWidth(18)
        qty_lbl.setAlignment(Qt.AlignCenter)
        qty_lbl.setStyleSheet(f"color:{T('text')}; font-weight:bold; font-size:10px;")

        plus = QPushButton("+")
        plus.setFixedSize(22, 22)
        plus.setStyleSheet(f"background:{T('success')}; color:#fff; border-radius:4px; font-weight:bold;")
        plus.setCursor(QCursor(Qt.PointingHandCursor))
        plus.clicked.connect(lambda _, c=ci: self._inc(c))

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(22, 22)
        del_btn.setStyleSheet("background:#E74C3C; color:#fff; border-radius:4px; font-size:8px;")
        del_btn.setCursor(QCursor(Qt.PointingHandCursor))
        del_btn.clicked.connect(lambda _, c=ci: self._remove(c))

        price_lbl = QLabel(f"₹{ci['price']*ci['quantity']:.0f}")
        price_lbl.setStyleSheet(f"color:{T('accent')}; font-weight:bold; font-size:9px;")

        for w in [minus, qty_lbl, plus, del_btn, price_lbl]:
            row.addWidget(w)
        return frame

    def _inc(self, ci):
        ci["quantity"] += 1
        self.refresh(); self.updated.emit()

    def _dec(self, ci):
        if ci["quantity"] > 1:
            ci["quantity"] -= 1
        else:
            cart_remove(ci["id"])
        self.refresh(); self.updated.emit()

    def _remove(self, ci):
        cart_remove(ci["id"])
        self.refresh(); self.updated.emit()

    def _clear_cart(self):
        global cart
        cart.clear()
        self.refresh(); self.updated.emit()


# ══════════════════════════════════════════════════════════════════════════════
#  Menu Screen
# ══════════════════════════════════════════════════════════════════════════════
class MenuScreen(QWidget):
    go_checkout = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_cat = list(MENU_DATA.keys())[0]
        self._build()
        self.show_category(self._current_cat)
        # Pre-warm image cache for the first visible category in background
        first_cat = self._current_cat
        QTimer.singleShot(500, lambda: preload_images(
            MENU_DATA.get(first_cat, []), category=first_cat))

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left sidebar (categories) ──────────────────────────
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet(f"background:{T('sidebar')};")
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(8, 12, 8, 12)
        sb_layout.setSpacing(4)

        logo_lbl = QLabel("🍽️ TWIN T")
        logo_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        logo_lbl.setStyleSheet(f"color:{T('primary')}; padding:4px;")
        sb_layout.addWidget(logo_lbl)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{T('border')};")
        sb_layout.addWidget(sep)

        self.cat_buttons: dict = {}
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setStyleSheet("background:transparent; border:none;")
        cat_widget = QWidget()
        cat_vbox   = QVBoxLayout(cat_widget)
        cat_vbox.setSpacing(2)

        for cat in MENU_DATA.keys():
            icon = CATEGORY_ICONS.get(cat, "🍽️")
            btn  = QPushButton(f" {icon}  {cat}")
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 9))
            btn.setStyleSheet(self._cat_btn_style(False))
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda _, c=cat: self.show_category(c))
            cat_vbox.addWidget(btn)
            self.cat_buttons[cat] = btn

        cat_vbox.addStretch()
        cat_scroll.setWidget(cat_widget)
        sb_layout.addWidget(cat_scroll, 1)

        # ── search bar below categories ────────────────────────
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search food…")
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{ background:{T('card')}; color:{T('text')};
                border:1px solid {T('border')}; border-radius:8px; padding:6px; font-size:11px; }}
        """)
        self.search_bar.textChanged.connect(self._search)
        sb_layout.addWidget(self.search_bar)

        root.addWidget(self.sidebar)

        # ── Centre content ─────────────────────────────────────
        centre = QWidget()
        centre.setStyleSheet(f"background:{T('bg')};")
        c_vbox = QVBoxLayout(centre)
        c_vbox.setContentsMargins(16, 12, 8, 12)
        c_vbox.setSpacing(10)

        # top bar
        top_bar = QHBoxLayout()
        self.cat_title = QLabel("Category")
        self.cat_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.cat_title.setStyleSheet(f"color:{T('text')};")
        top_bar.addWidget(self.cat_title)
        top_bar.addStretch()

        self.theme_btn = None   # themes removed

        fav_btn = QPushButton("❤ Favourites")
        fav_btn.setStyleSheet(f"""
            QPushButton {{ background:#E74C3C; color:#fff;
                border-radius:8px; padding:5px 12px; font-size:10px; }}
        """)
        fav_btn.setCursor(QCursor(Qt.PointingHandCursor))
        fav_btn.clicked.connect(self.show_favorites)
        top_bar.addWidget(fav_btn)
        c_vbox.addLayout(top_bar)

        # Today's special banner
        sp_item = MENU_DATA[TODAY_SPECIAL["category"]][0]
        special_frame = self._make_special_banner(sp_item)
        c_vbox.addWidget(special_frame)

        # scrollable grid of food cards
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setStyleSheet("background:transparent; border:none;")
        self.cards_container = QWidget()
        self.cards_grid      = QGridLayout(self.cards_container)
        self.cards_grid.setSpacing(14)
        self.cards_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.cards_scroll.setWidget(self.cards_container)
        c_vbox.addWidget(self.cards_scroll, 1)

        root.addWidget(centre, 1)

        # ── Right cart panel ───────────────────────────────────
        self.cart_panel = CartPanel()
        self.cart_panel.checkout_clicked.connect(self.go_checkout)
        self.cart_panel.updated.connect(self._on_cart_update)
        root.addWidget(self.cart_panel)

    def _cat_btn_style(self, active: bool) -> str:
        bg  = T("primary") if active else "transparent"
        col = "#1A0303"    if active else T("sidebar_text")
        return f"""
            QPushButton {{ background:{bg}; color:{col};
                border:none; border-radius:8px;
                padding:8px 10px; text-align:left; font-size:9px; }}
            QPushButton:hover {{ background:{T("primary")}; color:#1A0303; }}
        """

    def _make_special_banner(self, item: dict) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(80)
        frame.setStyleSheet(f"""
            QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #C0392B, stop:1 #F39C12);
                border-radius:12px; }}
        """)
        row = QHBoxLayout(frame)
        lbl_icon = QLabel("👑")
        lbl_icon.setFont(QFont("Segoe UI Emoji", 28))
        row.addWidget(lbl_icon)
        text_col = QVBoxLayout()
        t1 = QLabel("Today's Special")
        t1.setFont(QFont("Segoe UI", 9))
        t1.setStyleSheet("color:rgba(255,255,255,0.8);")
        t2 = QLabel(f"{item['name']}")
        t2.setFont(QFont("Segoe UI", 13, QFont.Bold))
        t2.setStyleSheet("color:#fff;")
        t3 = QLabel(f"₹{item['price']}  •  {TODAY_SPECIAL['discount']}% OFF  🎉")
        t3.setFont(QFont("Segoe UI", 10))
        t3.setStyleSheet("color:#FFD700;")
        text_col.addWidget(t1); text_col.addWidget(t2); text_col.addWidget(t3)
        row.addLayout(text_col, 1)
        add_btn = QPushButton("Order Now")
        add_btn.setFixedSize(100, 36)
        add_btn.setStyleSheet("""
            QPushButton { background:#D4AC0D; color:#1A0303;
                border-radius:8px; font-weight:bold; }
            QPushButton:hover { background:#F5D060; color:#1A0303; }
        """)
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))
        add_btn.clicked.connect(lambda: self._add_item(item, "Biryanis"))
        row.addWidget(add_btn)
        return frame

    def show_category(self, cat: str):
        self._current_cat = cat
        self.cat_title.setText(f"{CATEGORY_ICONS.get(cat,'')}  {cat}")
        for c, btn in self.cat_buttons.items():
            btn.setChecked(c == cat)
            btn.setStyleSheet(self._cat_btn_style(c == cat))
        self._populate_cards(MENU_DATA[cat], cat)
        # Warm the image cache for this category
        QTimer.singleShot(200, lambda: preload_images(MENU_DATA.get(cat, []), category=cat))

    def _populate_cards(self, items: list, category: str):
        # clear grid
        while self.cards_grid.count():
            child = self.cards_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        cols = 4
        for idx, item in enumerate(items):
            card = FoodCard(item, category)
            card.add_to_cart.connect(lambda i, c=category: self._add_item(i, c))
            card.toggle_fav.connect(self._toggle_fav)
            self.cards_grid.addWidget(card, idx // cols, idx % cols)

    def _add_item(self, item: dict, category: str):
        cart_add(item)
        self.cart_panel.refresh()
        Toast(f"✓  {item['name']} added to cart", self)
        # recommendations
        recs = RECOMMENDATIONS.get(category, [])
        if recs:
            all_items = {i["id"]: (i, c) for c, lst in MENU_DATA.items() for i in lst}
            rec_items = [all_items[r][0] for r in recs if r in all_items]
            if rec_items:
                QTimer.singleShot(700, lambda: self._show_recs(rec_items))

    def _show_recs(self, rec_items: list):
        dlg = RecommendationDialog(rec_items, self)
        if dlg.exec():
            for ri in dlg.selected:
                cart_add(ri)
            self.cart_panel.refresh()

    def _toggle_fav(self, item_id: str):
        added = toggle_favorite(item_id)
        action = "added to" if added else "removed from"
        Toast(f"{'❤' if added else '♡'}  {action} favourites", self)

    def show_favorites(self):
        favs = load_favorites()
        all_items = {i["id"]: (i, c) for c, lst in MENU_DATA.items() for i in lst}
        fav_items  = [(all_items[fid][0], all_items[fid][1]) for fid in favs if fid in all_items]
        dlg = FavoritesDialog(fav_items, self)
        dlg.exec()

    def _search(self, text: str):
        if not text.strip():
            self.show_category(self._current_cat)
            return
        text = text.lower()
        results = []
        for cat, items in MENU_DATA.items():
            for item in items:
                if (text in item["name"].lower() or text in cat.lower()):
                    results.append((item, cat))
        self.cat_title.setText(f"🔍 Results for \"{text}\"")
        while self.cards_grid.count():
            child = self.cards_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        cols = 4
        for idx, (item, cat) in enumerate(results):
            card = FoodCard(item, cat)
            card.add_to_cart.connect(lambda i, c=cat: self._add_item(i, c))
            card.toggle_fav.connect(self._toggle_fav)
            self.cards_grid.addWidget(card, idx // cols, idx % cols)

    def _on_cart_update(self):
        pass  # could update badge etc.

    def set_theme(self):
        self.cart_panel.setStyleSheet(f"background:{T('sidebar')};")
        self.sidebar.setStyleSheet(f"background:{T('sidebar')};")
        self.theme_btn.setText("☀ Light" if theme is DARK else "🌙 Dark")


# ══════════════════════════════════════════════════════════════════════════════
#  Recommendation Dialog
# ══════════════════════════════════════════════════════════════════════════════
class RecommendationDialog(QDialog):
    def __init__(self, items: list, parent=None):
        super().__init__(parent)
        self.selected = []
        self.setWindowTitle("Customers Also Enjoy 🤤")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setStyleSheet(f"background:{T('bg')};")
        root = QVBoxLayout(self)
        root.addWidget(make_label("🤖  Smart Recommendations", 14, True,
                                  "primary", Qt.AlignCenter))
        root.addWidget(make_label("Customers who ordered this also loved:",
                                  10, False, "text2", Qt.AlignCenter))
        self.checks = {}
        for item in items[:4]:
            cb = QCheckBox(f"  {item['name']}  — ₹{item['price']}")
            cb.setStyleSheet(f"color:{T('text')}; font-size:11px;")
            root.addWidget(cb)
            self.checks[item["id"]] = (cb, item)
        row = QHBoxLayout()
        skip = make_btn("Skip", "#888")
        add  = make_btn("Add Selected 🛒")
        skip.clicked.connect(self.reject)
        add.clicked.connect(self._add_selected)
        row.addWidget(skip); row.addWidget(add)
        root.addLayout(row)

    def _add_selected(self):
        self.selected = [item for (cb, item) in self.checks.values() if cb.isChecked()]
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  Favorites Dialog
# ══════════════════════════════════════════════════════════════════════════════
class FavoritesDialog(QDialog):
    def __init__(self, fav_items: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("❤  My Favourites")
        self.setMinimumSize(400, 350)
        self.setStyleSheet(f"background:{T('bg')};")
        root = QVBoxLayout(self)
        root.addWidget(make_label("❤  Favourite Items", 16, True, "primary", Qt.AlignCenter))
        if not fav_items:
            root.addWidget(make_label("No favourites yet. Tap ♡ on any item!", 11,
                                      False, "text2", Qt.AlignCenter))
        else:
            for item, cat in fav_items:
                lbl = QLabel(f"  {CATEGORY_EMOJI.get(cat,'🍽️')}  {item['name']}  —  ₹{item['price']}")
                lbl.setStyleSheet(f"""
                    background:{T('card')}; color:{T('text')}; border-radius:8px;
                    padding:8px; font-size:11px; border:1px solid {T('border')};
                """)
                root.addWidget(lbl)
        root.addStretch()
        close_btn = make_btn("Close")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)


# ══════════════════════════════════════════════════════════════════════════════
#  Checkout / Customer Details Screen
# ══════════════════════════════════════════════════════════════════════════════
class CheckoutScreen(QWidget):
    order_placed = Signal(dict)
    go_back      = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{T('bg')};")
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 20, 40, 20)
        root.setSpacing(14)

        root.addWidget(make_label("🧾  Checkout", 22, True, "primary", Qt.AlignCenter))

        # two-column layout
        cols = QHBoxLayout()
        cols.setSpacing(24)

        # ── left: customer details ─────────────────────────────
        left = QFrame()
        left.setStyleSheet(f"""
            QFrame {{ background:{T('card')}; border-radius:14px;
                border:1px solid {T('border')}; padding:12px; }}
        """)
        lf = QVBoxLayout(left)
        lf.setSpacing(10)
        lf.addWidget(make_label("👤  Customer Details", 13, True))

        self.name_in  = self._field("Customer Name *")
        self.phone_in = self._field("Phone Number * (10 digits)")
        self.email_in = self._field("Email Address (optional)")
        self.note_in  = QTextEdit()
        self.note_in.setPlaceholderText("Special Instructions (e.g. less spicy, no onions…)")
        self.note_in.setFixedHeight(70)
        self.note_in.setStyleSheet(f"""
            QTextEdit {{ background:{T('bg')}; color:{T('text')};
                border:1px solid {T('border')}; border-radius:8px; padding:6px; font-size:11px; }}
        """)

        for w in [self.name_in, self.phone_in, self.email_in, self.note_in]:
            lf.addWidget(w)
        lf.addStretch()
        cols.addWidget(left, 1)

        # ── right: order summary ───────────────────────────────
        right = QFrame()
        right.setStyleSheet(f"""
            QFrame {{ background:{T('card')}; border-radius:14px;
                border:1px solid {T('border')}; padding:12px; }}
        """)
        rf = QVBoxLayout(right)
        rf.addWidget(make_label("📋  Order Summary", 13, True))

        self.summary_scroll = QScrollArea()
        self.summary_scroll.setWidgetResizable(True)
        self.summary_scroll.setStyleSheet("background:transparent; border:none;")
        self.summary_widget = QWidget()
        self.summary_layout = QVBoxLayout(self.summary_widget)
        self.summary_layout.setSpacing(4)
        self.summary_scroll.setWidget(self.summary_widget)
        rf.addWidget(self.summary_scroll, 1)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{T('border')};")
        rf.addWidget(sep)

        self.lbl_sub      = make_label("Subtotal : ₹0",   10)
        self.lbl_disc     = make_label("",                 10, False, "success")
        self.lbl_gst      = make_label("GST (5%) : ₹0",   10)
        self.lbl_final    = make_label("TOTAL    : ₹0",   14, True, "primary")
        for lbl in [self.lbl_sub, self.lbl_disc, self.lbl_gst, self.lbl_final]:
            rf.addWidget(lbl)

        self.lbl_offer    = make_label("", 10, False, "success")
        rf.addWidget(self.lbl_offer)
        cols.addWidget(right, 1)
        root.addLayout(cols, 1)

        # ── buttons ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        back_btn  = make_btn("← Back to Menu", "#666")
        place_btn = make_btn("✅  Place Order & Generate Bill", T("primary"), size=12)
        back_btn.clicked.connect(self.go_back)
        place_btn.clicked.connect(self._place_order)
        btn_row.addWidget(back_btn)
        btn_row.addStretch()
        btn_row.addWidget(place_btn)
        root.addLayout(btn_row)

    def _field(self, placeholder: str) -> QLineEdit:
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        f.setStyleSheet(f"""
            QLineEdit {{ background:{T('bg')}; color:{T('text')};
                border:1px solid {T('border')}; border-radius:8px;
                padding:8px; font-size:11px; }}
        """)
        return f

    def refresh_summary(self):
        while self.summary_layout.count():
            child = self.summary_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for ci in cart:
            row_lbl = QLabel(f"• {ci['name']}  ×{ci['quantity']}  —  ₹{ci['price']*ci['quantity']:.0f}")
            row_lbl.setStyleSheet(f"color:{T('text')}; font-size:10px;")
            self.summary_layout.addWidget(row_lbl)
        self.summary_layout.addStretch()

        sub = cart_subtotal()
        disc, gst, final, specials = calc_totals(sub)
        self.lbl_sub.setText(f"Subtotal  : ₹{sub:.0f}")
        self.lbl_disc.setText(f"Discount  : -₹{disc:.0f}  🎉" if disc else "")
        self.lbl_gst.setText(f"GST (5%) : ₹{gst:.2f}")
        self.lbl_final.setText(f"TOTAL    : ₹{final:.2f}")
        offer_text = ""
        if specials:
            offer_text = "🎁 Complimentary: " + ", ".join(specials)
        if sub > 2000:
            offer_text = "🎉 10% Discount Applied!  " + offer_text
        self.lbl_offer.setText(offer_text)

    def _place_order(self):
        name  = self.name_in.text().strip()
        phone = self.phone_in.text().strip()
        email = self.email_in.text().strip()
        note  = self.note_in.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Validation", "Please enter your name.")
            return
        if not phone.isdigit() or len(phone) != 10:
            QMessageBox.warning(self, "Validation",
                                "Phone number must be exactly 10 digits.")
            return
        if not cart:
            QMessageBox.warning(self, "Empty Cart", "Your cart is empty!")
            return

        sub = cart_subtotal()
        disc, gst, final, specials = calc_totals(sub)
        invoice_no = get_next_invoice_number()
        customer   = {"name": name, "phone": phone,
                      "email": email, "instructions": note}

        # save records
        save_customer(name, phone, email)
        order_record = {
            "invoice":       invoice_no,
            "customer_name": name,
            "phone":         phone,
            "email":         email,
            "items":         list(cart),
            "subtotal":      sub,
            "discount":      disc,
            "gst":           gst,
            "total":         final,
            "date":          datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        save_order(order_record)

        # generate PDF
        pdf_path = generate_pdf_bill(invoice_no, customer, list(cart),
                                     sub, disc, gst, final, specials)

        self.order_placed.emit({
            "invoice":   invoice_no,
            "customer":  customer,
            "sub":       sub,
            "discount":  disc,
            "gst":       gst,
            "final":     final,
            "specials":  specials,
            "pdf_path":  pdf_path,
        })


# ══════════════════════════════════════════════════════════════════════════════
#  Order Confirmation Screen
# ══════════════════════════════════════════════════════════════════════════════
class ConfirmationScreen(QWidget):
    new_order    = Signal()
    give_feedback = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._order_data = {}
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{T('bg')};")
        root = QVBoxLayout(self)
        root.setContentsMargins(60, 30, 60, 30)
        root.setSpacing(16)
        root.setAlignment(Qt.AlignCenter)

        lbl_tick = QLabel("✅")
        lbl_tick.setFont(QFont("Segoe UI Emoji", 60))
        lbl_tick.setAlignment(Qt.AlignCenter)
        root.addWidget(lbl_tick)

        root.addWidget(make_label("Order Placed Successfully!", 24, True,
                                  "primary", Qt.AlignCenter))
        self.lbl_invoice = make_label("", 12, False, "text2", Qt.AlignCenter)
        root.addWidget(self.lbl_invoice)
        self.lbl_total   = make_label("", 16, True, "success", Qt.AlignCenter)
        root.addWidget(self.lbl_total)
        self.lbl_pdf     = make_label("", 10, False, "text2", Qt.AlignCenter)
        root.addWidget(self.lbl_pdf)
        self.lbl_specials = make_label("", 12, False, "success", Qt.AlignCenter)
        root.addWidget(self.lbl_specials)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        fb_btn  = make_btn("⭐  Give Feedback", T("accent"))
        new_btn = make_btn("🍽️  New Order",     T("primary"))
        fb_btn.clicked.connect(self._feedback)
        new_btn.clicked.connect(self.new_order)
        btn_row.addWidget(fb_btn); btn_row.addWidget(new_btn)
        root.addLayout(btn_row)

    def load(self, data: dict):
        self._order_data = data
        self.lbl_invoice.setText(f"Invoice # {data['invoice']}")
        self.lbl_total.setText(f"Total Paid: ₹{data['final']:.2f}")
        self.lbl_pdf.setText(f"Bill saved: {data.get('pdf_path','')}")
        specials = data.get("specials", [])
        if specials:
            self.lbl_specials.setText("🎁 Complimentary: " + ", ".join(specials))
        if data.get("discount"):
            self.lbl_specials.setText(
                self.lbl_specials.text() + f"\n🎉 10% Discount applied!"
            )

    def _feedback(self):
        self.give_feedback.emit(self._order_data)


# ══════════════════════════════════════════════════════════════════════════════
#  Feedback Dialog
# ══════════════════════════════════════════════════════════════════════════════
class FeedbackDialog(QDialog):
    def __init__(self, customer: dict, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle("⭐  Customer Feedback")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setStyleSheet("QDialog { background:#4A1515; } QLabel { color:#F5E6C8; }")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(make_label("⭐  Rate Your Experience", 16, True,
                                  "primary", Qt.AlignCenter))

        # star rating
        star_row = QHBoxLayout()
        star_row.setAlignment(Qt.AlignCenter)
        self._rating = 0
        self._star_btns = []
        for i in range(1, 6):
            sb = QPushButton("★")
            sb.setFont(QFont("Georgia", 26, QFont.Bold))
            sb.setFixedSize(50, 50)
            sb.setStyleSheet("background:transparent; border:none; color:#555; padding:0;")
            sb.setCursor(QCursor(Qt.PointingHandCursor))
            sb.clicked.connect(lambda _, r=i: self._set_rating(r))
            star_row.addWidget(sb)
            self._star_btns.append(sb)
        root.addLayout(star_row)

        # tagline label
        self._tag_lbl = QLabel("")
        self._tag_lbl.setFont(QFont("Georgia", 12, QFont.Bold))
        self._tag_lbl.setAlignment(Qt.AlignCenter)
        self._tag_lbl.setFixedHeight(26)
        root.addWidget(self._tag_lbl)

        self.comment = QTextEdit()
        self.comment.setPlaceholderText("Tell us about your experience…")
        self.comment.setFixedHeight(100)
        self.comment.setStyleSheet("""
            QTextEdit { background:#5C1C1C; color:#F5E6C8;
                border:1px solid #8B5A2B; border-radius:8px; padding:8px;
                font-size:11px; }
        """)
        root.addWidget(self.comment)

        btn_row = QHBoxLayout()
        skip = make_btn("Skip", "#888")
        sub  = make_btn("Submit ⭐")
        skip.clicked.connect(self.reject)
        sub.clicked.connect(self._submit)
        btn_row.addWidget(skip); btn_row.addWidget(sub)
        root.addLayout(btn_row)
        self._set_rating(0)

    _TAGLINES = {
        0: ("", "#888"),
        1: ("😞  Terrible — Very disappointed", "#E74C3C"),
        2: ("😕  Bad — Needs improvement", "#E67E22"),
        3: ("😐  Okay — Could be better", "#F1C40F"),
        4: ("😊  Good — Enjoyed it!", "#2ECC71"),
        5: ("🤩  Excellent — Absolutely loved it!", "#27AE60"),
    }

    def _set_rating(self, r: int):
        self._rating = r
        for i, sb in enumerate(self._star_btns):
            if i < r:
                sb.setText("★")
                sb.setStyleSheet("background:transparent; border:none; color:#F39C12; padding:0;")
            else:
                sb.setText("☆")
                sb.setStyleSheet("background:transparent; border:none; color:#888; padding:0;")
        text, color = self._TAGLINES.get(r, ("", "#888"))
        self._tag_lbl.setText(text)
        self._tag_lbl.setStyleSheet(f"color:{color};")

    def _submit(self):
        if self._rating == 0:
            QMessageBox.warning(self, "Rating Required",
                                "Please select a star rating before submitting! ⭐")
            return
        save_feedback(
            self.customer.get("name",""),
            self.customer.get("phone",""),
            self._rating,
            self.comment.toPlainText().strip(),
        )
        QMessageBox.information(self, "Thank You!",
                                "Thank you for your valuable feedback! 🙏")
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  Order History Screen
# ══════════════════════════════════════════════════════════════════════════════
class HistoryScreen(QWidget):
    go_back = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{T('bg')};")
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(make_label("📊  Order History", 20, True, "primary"))
        hdr.addStretch()
        back_btn = make_btn("← Back", "#666")
        back_btn.clicked.connect(self.go_back)
        hdr.addWidget(back_btn)
        root.addLayout(hdr)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Search by name or phone…")
        self.search.setStyleSheet(f"""
            QLineEdit {{ background:{T('card')}; color:{T('text')};
                border:1px solid {T('border')}; border-radius:8px;
                padding:8px; font-size:11px; max-width:300px; }}
        """)
        self.search.textChanged.connect(self._search)
        root.addWidget(self.search)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Invoice", "Customer", "Phone", "Items", "Total (₹)", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background:{T('card')}; color:{T('text')};
                border:1px solid {T('border')}; border-radius:8px;
                gridline-color:{T('border')}; font-size:10px; }}
            QHeaderView::section {{ background:{T('primary')}; color:#fff;
                padding:6px; font-size:10px; }}
        """)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        root.addWidget(self.table, 1)

        # Feedback section
        root.addWidget(make_label("⭐  Customer Feedback", 14, True, "primary"))
        self.fb_table = QTableWidget()
        self.fb_table.setColumnCount(5)
        self.fb_table.setHorizontalHeaderLabels(
            ["Name", "Phone", "Rating", "Comment", "Date"])
        self.fb_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fb_table.setStyleSheet(self.table.styleSheet())
        self.fb_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.fb_table.setFixedHeight(160)
        root.addWidget(self.fb_table)

    def load_data(self):
        self._fill_orders(load_orders())
        self._fill_feedback(load_feedback())

    def _fill_orders(self, orders: list):
        self.table.setRowCount(0)
        for o in reversed(orders):
            row = self.table.rowCount()
            self.table.insertRow(row)
            items_str = ", ".join(
                f"{ci['name']} x{ci['quantity']}" for ci in o.get("items", []))
            for col, val in enumerate([
                o.get("invoice",""), o.get("customer_name",""),
                o.get("phone",""), items_str,
                f"₹{o.get('total',0):.2f}", o.get("date",""),
            ]):
                self.table.setItem(row, col, QTableWidgetItem(val))

    def _fill_feedback(self, feedbacks: list):
        self.fb_table.setRowCount(0)
        for fb in reversed(feedbacks):
            row = self.fb_table.rowCount()
            self.fb_table.insertRow(row)
            stars = "⭐" * fb.get("rating", 0)
            for col, val in enumerate([
                fb.get("name",""), fb.get("phone",""), stars,
                fb.get("comment",""), fb.get("date",""),
            ]):
                self.fb_table.setItem(row, col, QTableWidgetItem(val))

    def _search(self, text: str):
        if not text.strip():
            self._fill_orders(load_orders())
            return
        self._fill_orders(search_orders(text))


# ══════════════════════════════════════════════════════════════════════════════
#  Main Window
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🍽️  TWIN T Restaurant")
        self.setMinimumSize(1280, 760)
        self.setStyleSheet(f"QMainWindow {{ background:{T('bg')}; }}")
        self._build()

    def _build(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.menu_screen = MenuScreen()
        self.checkout_screen = CheckoutScreen()
        self.confirm_screen  = ConfirmationScreen()
        self.history_screen  = HistoryScreen()

        self.stack.addWidget(self.menu_screen)       # 0
        self.stack.addWidget(self.checkout_screen)   # 1
        self.stack.addWidget(self.confirm_screen)    # 2
        self.stack.addWidget(self.history_screen)    # 3

        # wire signals
        self.menu_screen.go_checkout.connect(self._go_checkout)
        self.checkout_screen.go_back.connect(lambda: self.stack.setCurrentIndex(0))
        self.checkout_screen.order_placed.connect(self._order_placed)
        self.confirm_screen.new_order.connect(self._new_order)
        self.confirm_screen.give_feedback.connect(self._give_feedback)
        self.history_screen.go_back.connect(lambda: self.stack.setCurrentIndex(0))

        # history button in menu bar
        self.hist_action = self.menuBar().addAction("📊 Order History")
        self.hist_action.triggered.connect(self._show_history)

        self.stack.setCurrentIndex(0)

    def _go_checkout(self):
        if not cart:
            QMessageBox.information(self, "Empty Cart",
                                    "Please add items to cart first!")
            return
        self.checkout_screen.refresh_summary()
        self.stack.setCurrentIndex(1)

    def _order_placed(self, data: dict):
        global cart
        self.confirm_screen.load(data)
        cart.clear()
        self.menu_screen.cart_panel.refresh()
        self.stack.setCurrentIndex(2)

    def _new_order(self):
        self.checkout_screen.name_in.clear()
        self.checkout_screen.phone_in.clear()
        self.checkout_screen.email_in.clear()
        self.checkout_screen.note_in.clear()
        self.stack.setCurrentIndex(0)

    def _give_feedback(self, data: dict):
        dlg = FeedbackDialog(data.get("customer", {}), self)
        dlg.exec()

    def _show_history(self):
        self.history_screen.load_data()
        self.stack.setCurrentIndex(3)



# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TWIN T Restaurant")
    app.setStyle("Fusion")

    # show welcome portal full-screen
    splash = SplashScreen()
    splash.showFullScreen()

    win = MainWindow()

    def on_splash_done():
        splash.close()
        win.showMaximized()

    splash.done.connect(on_splash_done)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
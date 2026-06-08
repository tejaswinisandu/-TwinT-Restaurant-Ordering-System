# 👑 TwinT Restaurant — Self-Ordering System

> *Taste Beyond Expectations*

A full-featured **restaurant self-ordering desktop application** built with Python and PySide6. Designed for dine-in customers to browse the menu, customize orders, and checkout — all without waiting for a waiter.

## ✨ Features

- 🎨 **3 Premium Themes** — Crimson & Gold, Royal Navy & Gold, Emerald & Antique Gold
- 🍛 **Full Menu** — 14 categories, 100+ dishes with real food photos (via Pexels API)
- 🛒 **Smart Cart** — Add, remove, adjust quantities in real time
- ❤️ **Favourites** — Save your favourite dishes for quick reorder
- 🤖 **AI Recommendations** — Suggests dishes based on your order
- 📋 **Order History** — View all past orders with details
- ⭐ **Feedback System** — Rate your experience with star ratings & taglines
- 🔍 **Live Search** — Search any dish instantly
- 🧾 **GST & Billing** — Auto-calculated with 5% GST
- 📦 **Today's Special** — Highlighted deal on the home screen

---

## 🖥️ Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.11+ | Core language |
| PySide6 | GUI framework (Qt6) |
| Pexels API | Food images |
| JSON | Order & feedback storage |

---

## 🚀 Getting Started

### Prerequisites
```bash
pip install PySide6
```

### Run the App
```bash
python main.py
```

### First-Time Image Setup
```bash
python image_loader.py   # clears cache, fresh download starts on next run
```

---

## 📁 Project Structure

```
TwinT-Restaurant/
├── main.py              # Main application
├── image_loader.py      # Pexels API image downloader
├── logo.png             # Restaurant logo
├── image_cache/         # Auto-downloaded food photos (gitignored)
├── orders.json          # Saved orders (auto-generated)
└── feedback.json        # Customer feedback (auto-generated)
```

---

## 📸 Screenshots

> *Coming soon*

---

## 📜 License

This project is for educational and personal use.

---
<p align="center">Built with 🔥 by <b>Tejaswini Sandu & Tarun Gunda</b> | Guntur, India</p></b></p>
<p align="center">
  <img src="logo.png" width="120"/>
</p>

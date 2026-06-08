"""
Run this script first to check which image sources work on your machine:
    python test_images.py
"""
import urllib.request, ssl, sys

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*',
}

TESTS = [
    ('Unsplash CDN',    'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=210&h=140&fit=crop&q=80'),
    ('TheMealDB API',   'https://www.themealdb.com/api/json/v1/1/search.php?s=biryani'),
    ('TheMealDB image', 'https://www.themealdb.com/images/media/meals/wyxwsp1486979827.jpg'),
    ('Pexels CDN',      'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?w=210&h=140'),
]

print("Testing image sources...\n")
for name, url in TESTS:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = r.read(200)
            ct = r.headers.get('Content-Type', '')
            print(f"  ✓  {name}  ({ct[:30]})")
    except Exception as e:
        print(f"  ✗  {name}  → {e}")
print("\nDone. Share these results!")

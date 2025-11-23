import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image
import os

# ---------- CONFIG ----------
BASE = "https://malamoyo.com"  # 🔁 change if needed
LOGO_PATH = "/var/www/life/myshop/logo.jpg"       # your logo file in this folder
OUT_DIR = "qr_styled"        # output folder

# QR targets: label -> URL
QR_TARGETS = {
    "home":              f"{BASE}/?src=qr_event",
    "event_landing":     f"{BASE}/event/pop-up?src=qr_event",
    "all_products":      f"{BASE}/shop?src=qr_all",
    "pink_lady":         f"{BASE}/product/pink-lady?src=qr_pink_lady",
    "tobacco_and_ebony": f"{BASE}/product/tobacco-and-ebony?src=qr_tobacco_ebony",

}

# Gold + dark theme
FILL_COLOR = "#000000"   # black
BACK_COLOR = "#FFFFFF"   # white


def make_qr_with_logo(name: str, url: str, logo_path: str):
    # High error correction to survive the logo in the middle
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create base QR image with custom colors
    img_qr = qr.make_image(fill_color=FILL_COLOR, back_color=BACK_COLOR).convert("RGB")
    qr_width, qr_height = img_qr.size

    # Open and resize logo
    logo = Image.open(logo_path).convert("RGBA")

    # Logo should be about 20–25% of QR width
    logo_size = int(qr_width * 0.23)
    logo.thumbnail((logo_size, logo_size), Image.LANCZOS)

    # Calculate position (center)
    lx = (qr_width - logo.width) // 2
    ly = (qr_height - logo.height) // 2

    # Paste logo on QR, keeping transparency
    img_qr.paste(logo, (lx, ly), logo)

    # Save
    os.makedirs(OUT_DIR, exist_ok=True)
    filename = os.path.join(OUT_DIR, f"{name}_qr_gold.png")
    img_qr.save(filename)

    print(f"✅ {name}: {url}  -->  {filename}")


if __name__ == "__main__":
    if not os.path.exists(LOGO_PATH):
        raise SystemExit(f"❌ Logo file not found: {LOGO_PATH}")

    for name, url in QR_TARGETS.items():
        make_qr_with_logo(name, url, LOGO_PATH)

import qrcode
from PIL import Image
from pathlib import Path


def generate_qr_with_logo(data, filename):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # ✅ Resolve project app directory (app/)
    APP_DIR = Path(__file__).resolve().parents[1]  # goes up to /app
    STATIC_DIR = APP_DIR / "static"
    QR_DIR = STATIC_DIR / "qr"
    IMAGES_DIR = STATIC_DIR / "images"

    # ✅ Ensure QR dir exists
    QR_DIR.mkdir(parents=True, exist_ok=True)

    logo_path = IMAGES_DIR / "logo.png"

    if not logo_path.exists():
        raise FileNotFoundError(f"Logo not found at: {logo_path}")

    logo = Image.open(logo_path)

    qr_width, qr_height = qr_img.size
    logo_size = qr_width // 3
    logo = logo.resize((logo_size, logo_size))

    pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)

    qr_img.paste(logo, pos, mask=logo if logo.mode == "RGBA" else None)

    save_path = QR_DIR / filename
    qr_img.save(save_path)

    return str(save_path)

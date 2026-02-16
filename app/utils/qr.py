from pathlib import Path
from typing import cast

import qrcode
from PIL import Image


def generate_qr_with_logo(data: str, filename: str) -> str:
    # 1. Use direct attribute access or explicit import for constants
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # type: ignore
        box_size=20,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # 2. Cast the result to PIL.Image.Image so Pylance sees .convert()
    # The default factory for qrcode is a PIL-based image
    qr_img = cast(
        Image.Image, qr.make_image(fill_color="black", back_color="white")
    ).convert("RGB")

    APP_DIR = Path(__file__).resolve().parents[1]
    STATIC_DIR = APP_DIR / "static"
    QR_DIR = STATIC_DIR / "qr"
    IMAGES_DIR = STATIC_DIR / "images"

    QR_DIR.mkdir(parents=True, exist_ok=True)

    logo_path = IMAGES_DIR / "logo.png"

    if not logo_path.exists():
        raise FileNotFoundError(f"Logo not found at: {logo_path}")

    logo = Image.open(logo_path)

    qr_width, qr_height = qr_img.size
    logo_size = qr_width // 3
    logo = logo.resize((logo_size, logo_size))

    pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)

    # Use the logo itself as a mask if it has an alpha channel
    mask = logo if logo.mode == "RGBA" else None
    qr_img.paste(logo, pos, mask=mask)

    save_path = QR_DIR / filename
    qr_img.save(save_path)

    return str(save_path)

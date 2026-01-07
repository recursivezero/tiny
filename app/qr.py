import qrcode
from PIL import Image


def generate_qr_with_logo(data, filename):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    logo = Image.open("app/static/images/logo.png")

    qr_width, qr_height = qr_img.size
    logo_size = qr_width // 3
    logo = logo.resize((logo_size, logo_size))

    pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)

    qr_img.paste(logo, pos, mask=logo if logo.mode == "RGBA" else None)

    save_path = f"app/static/qr/{filename}"
    qr_img.save(save_path)

    return save_path

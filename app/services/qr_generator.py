"""QR Code generation utility."""
import io
import secrets
import qrcode
from qrcode.image.pure import PyPNGImage


def build_qr_payload(name: str) -> str:
    """Build QR payload as: <name>|<random_hash>.

    The random part is intentionally not used for DB lookup right now; lookup uses
    the name prefix so older QR codes without the separator still work.
    """
    random_hash = secrets.token_hex(8)  # 16 hex chars
    return f"{name}|{random_hash}"


def generate_qr_code_blob(name: str) -> bytes:
    payload = build_qr_payload(name)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    
    # Create image and save to bytes buffer
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.getvalue()


def generate_qr_code_file(name: str, filepath: str) -> None:
    payload = build_qr_payload(name)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filepath)

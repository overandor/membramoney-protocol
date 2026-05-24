"""QR code and barcode generation for MEMBRA FileLife."""
import base64
import io

try:
    import qrcode
    from qrcode.image.pure import PyPNGImage
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False


def generate_qr_base64(data: str, box_size: int = 8, border: int = 4) -> str:
    """Generate a QR code and return as data:image/png;base64 string."""
    if not QR_AVAILABLE:
        return _placeholder_png_b64("QR")
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def generate_barcode_base64(sku: str) -> str:
    """Generate a Code128 barcode from SKU and return as data:image/png;base64 string."""
    if not BARCODE_AVAILABLE:
        return _placeholder_png_b64("BAR")
    try:
        from PIL import Image
        CODE128 = barcode.get_barcode_class("code128")
        buf = io.BytesIO()
        writer = ImageWriter()
        bc = CODE128(sku, writer=writer)
        options = {"module_height": 12.0, "module_width": 0.4, "quiet_zone": 2.0, "text_distance": 4.0, "font_size": 8}
        bc.write(buf, options=options)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return _placeholder_png_b64("BAR")


def _placeholder_png_b64(label: str) -> str:
    """Return a minimal 1x1 white PNG as placeholder when libraries are missing."""
    # Minimal valid PNG (1x1 white pixel)
    PNG_1X1 = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff"
        b"?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    b64 = base64.b64encode(PNG_1X1).decode()
    return f"data:image/png;base64,{b64}"

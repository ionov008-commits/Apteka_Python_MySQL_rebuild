import os
import qrcode

ORDERS_DIR = os.path.join("static", "images", "orders")

def generate_order_qr(order_id: int) -> str:
    """Генерирует QR-код с ID заказа и сохраняет в static/images/orders/{order_id}.png"""
    os.makedirs(ORDERS_DIR, exist_ok=True)
    file_path = os.path.join(ORDERS_DIR, f"{order_id}.png")

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=2,
    )
    qr.add_data(str(order_id))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(file_path)

    return f"/static/images/orders/{order_id}.png"
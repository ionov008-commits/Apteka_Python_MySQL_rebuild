import os
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    user_role = request.cookies.get("user_role")
    if not user_id or user_role != "admin":
        return RedirectResponse(url="/account/login", status_code=303)

    users = db.query(models.User).all()
    pharmacies = db.query(models.Pharmacy).all()
    products = db.query(models.Product).order_by(models.Product.product_id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "users": users,
            "pharmacies": pharmacies,
            "products": products,
            "title": "Панель администратора"
        }
    )


@router.post("/product/add")
async def add_product(
    name: str = Form(...),
    active_substance: Optional[str] = Form(None),
    form: str = Form(...),
    dosage: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    prescription_required: bool = Form(False),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    product = models.Product(
        name=name,
        active_substance=active_substance,
        form=form,
        dosage=dosage,
        description=description,
        prescription_required=1 if prescription_required else 0
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # Если загружен файл изображения
    if image_file and image_file.filename:
        folder = os.path.join("static", "images", "products")
        os.makedirs(folder, exist_ok=True)
        ext = os.path.splitext(image_file.filename)[1] or ".png"
        filename = f"{product.product_id}{ext}"
        file_path = os.path.join(folder, filename)

        content = await image_file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        product.image = filename
        db.commit()

    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.post("/user/delete/{user_id_to_delete}")
def delete_user(user_id_to_delete: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id_to_delete).first()
    if user and user.role != "admin":
        db.delete(user)
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)
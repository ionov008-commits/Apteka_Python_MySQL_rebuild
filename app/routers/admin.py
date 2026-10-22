from fastapi import APIRouter, Depends, Request, Form, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import os
import shutil

from app.db.database import get_db
from app.db import models

router = APIRouter(prefix='/admin', tags=['Admin'])
templates = Jinja2Templates(directory='templates')

def check_admin_access(request: Request):
    role = request.cookies.get('user_role')
    return role == 'admin'

@router.get('/dashboard')
def admin_dashboard(request: Request, error: Optional[str] = None, success: Optional[str] = None, db: Session = Depends(get_db)):
    if not check_admin_access(request):
        return RedirectResponse(url='/account/login', status_code=303)

    products = db.query(models.Product).order_by(models.Product.product_id.desc()).all()
    pharmacies = db.query(models.Pharmacy).all()
    users_count = db.query(models.User).count()

    return templates.TemplateResponse(
        request=request, name='admin/dashboard.html',
        context={
            'products': products,
            'pharmacies': pharmacies,
            'users_count': users_count,
            'error': error,
            'success': success,
            'title': 'Панель администратора'
        }
    )

@router.post('/products/add')
async def add_product(
    request: Request,
    name: str = Form(...),
    active_substance: Optional[str] = Form(None),
    form: str = Form(...),
    dosage: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    prescription_required: Optional[bool] = Form(False),
    image_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not check_admin_access(request):
        return RedirectResponse(url='/account/login', status_code=303)

    # 1. Валидация обязательных полей
    if not name.strip() or not form.strip() or not dosage.strip():
        return RedirectResponse(
            url='/admin/dashboard?error=Заполните+все+обязательные+поля+(Название,+Форма,+Дозировка)',
            status_code=303
        )

    if not image_file or not image_file.filename:
        return RedirectResponse(
            url='/admin/dashboard?error=Загрузка+изображения+препарата+обязательна',
            status_code=303
        )

    # 2. Проверка на дубликат (Название + Форма + Дозировка)
    existing_product = db.query(models.Product).filter(
        func.lower(models.Product.name) == name.strip().lower(),
        func.lower(models.Product.form) == form.strip().lower(),
        func.lower(models.Product.dosage) == dosage.strip().lower()
    ).first()

    if existing_product:
        return RedirectResponse(
            url=f'/admin/dashboard?error=Препарат+"{name.strip()}"+({form.strip()},+{dosage.strip()})+уже+есть+в+базе+(ID:+{existing_product.product_id})',
            status_code=303
        )

    # 3. Добавление записи в БД для генерации product_id
    new_product = models.Product(
        name=name.strip(),
        active_substance=active_substance.strip() if active_substance else None,
        form=form.strip(),
        dosage=dosage.strip() if dosage else None,
        description=description.strip() if description else None,
        prescription_required=bool(prescription_required),
        image=None  # Свойство display_image автоматически возьмет product_id.png
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # 4. Сохранение картинки под именем {product_id}.png
    upload_dir = os.path.join('static', 'images', 'products')
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, f"{new_product.product_id}.png")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image_file.file, buffer)

    return RedirectResponse(
        url=f'/admin/dashboard?success=Препарат+"{new_product.name}"+успешно+добавлен+(ID:+{new_product.product_id})',
        status_code=303
    )
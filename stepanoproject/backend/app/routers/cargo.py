

import uuid
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.cargo import CargoDocument
from app.models.order import Order
from app.models.user import User

router = APIRouter()

UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/orders/{order_id}/documents")
async def upload_document(
    order_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):


    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип файла. Разрешены: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )


    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимум: {settings.MAX_UPLOAD_SIZE_MB} МБ",
        )


    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")


    safe_filename = f"{uuid.uuid4()}.{ext}"
    file_path = UPLOAD_DIR / safe_filename
    file_path.write_bytes(content)

    doc = CargoDocument(
        order_id=order_id,
        uploader_id=current_user.id,
        filename=safe_filename,
        original_name=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        content_type=file.content_type or "application/octet-stream",
    )
    db.add(doc)
    await db.flush()

    return {
        "id": doc.id,
        "original_name": doc.original_name,
        "file_size": doc.file_size,
        "message": "Файл успешно загружен",
    }


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Скачивание документа."""
    result = await db.execute(select(CargoDocument).where(CargoDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")

    return FileResponse(
        doc.file_path,
        filename=doc.original_name,
        media_type=doc.content_type,
    )

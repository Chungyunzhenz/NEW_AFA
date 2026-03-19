import json
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.upload import ColumnMappingPreset
from ...schemas.upload import (
    ColumnMappingRequest,
    FileUploadResponse,
    ImportConfirmRequest,
    ImportPreviewResponse,
    ImportResultResponse,
    MappingPresetCreateRequest,
    MappingPresetResponse,
)
from ...services.file_upload_service import (
    confirm_import,
    parse_uploaded_file,
    preview_import,
)

router = APIRouter()


@router.post("/file", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    data_type: str = Query("trading", regex="^(trading|production|weather)$"),
):
    """Upload a CSV or Excel file for parsing."""
    if not file.filename:
        raise HTTPException(400, "No filename provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(400, f"Unsupported file type: .{ext}. Use CSV or Excel.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, "File is empty.")
    if len(contents) > 50 * 1024 * 1024:  # 50 MB limit
        raise HTTPException(400, "File exceeds 50 MB limit.")

    try:
        result = parse_uploaded_file(contents, file.filename, data_type)
    except Exception as exc:
        raise HTTPException(400, f"Failed to parse file: {exc}")

    return result


@router.post("/preview", response_model=ImportPreviewResponse)
def preview_upload(
    req: ColumnMappingRequest,
    db: Session = Depends(get_db),
):
    """Apply column mapping and validate rows."""
    try:
        result = preview_import(req.upload_id, req.data_type, req.mapping, db)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Preview failed: {exc}")

    return result


@router.post("/confirm", response_model=ImportResultResponse)
def confirm_upload(
    req: ImportConfirmRequest,
    db: Session = Depends(get_db),
):
    """Confirm and import validated data into the database."""
    try:
        result = confirm_import(req.upload_id, req.data_type, db, req.skip_errors)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Import failed: {exc}")

    return result


# ---- Mapping Presets CRUD ----

@router.get("/presets", response_model=List[MappingPresetResponse])
def list_presets(
    data_type: Optional[str] = Query(None, regex="^(trading|production|weather)$"),
    db: Session = Depends(get_db),
):
    """List saved column mapping presets."""
    q = db.query(ColumnMappingPreset)
    if data_type:
        q = q.filter(ColumnMappingPreset.data_type == data_type)
    presets = q.order_by(ColumnMappingPreset.created_at.desc()).all()

    result = []
    for p in presets:
        result.append(MappingPresetResponse(
            id=p.id,
            name=p.name,
            data_type=p.data_type,
            mapping=json.loads(p.mapping_json),
            created_at=p.created_at,
        ))
    return result


@router.post("/presets", response_model=MappingPresetResponse)
def create_preset(
    req: MappingPresetCreateRequest,
    db: Session = Depends(get_db),
):
    """Save a new column mapping preset."""
    existing = (
        db.query(ColumnMappingPreset)
        .filter(
            ColumnMappingPreset.name == req.name,
            ColumnMappingPreset.data_type == req.data_type,
        )
        .first()
    )
    if existing:
        existing.mapping_json = json.dumps(req.mapping, ensure_ascii=False)
        db.commit()
        db.refresh(existing)
        return MappingPresetResponse(
            id=existing.id,
            name=existing.name,
            data_type=existing.data_type,
            mapping=json.loads(existing.mapping_json),
            created_at=existing.created_at,
        )

    preset = ColumnMappingPreset(
        name=req.name,
        data_type=req.data_type,
        mapping_json=json.dumps(req.mapping, ensure_ascii=False),
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)

    return MappingPresetResponse(
        id=preset.id,
        name=preset.name,
        data_type=preset.data_type,
        mapping=json.loads(preset.mapping_json),
        created_at=preset.created_at,
    )


@router.delete("/presets/{preset_id}")
def delete_preset(
    preset_id: int,
    db: Session = Depends(get_db),
):
    """Delete a column mapping preset."""
    preset = db.query(ColumnMappingPreset).filter(ColumnMappingPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found.")

    db.delete(preset)
    db.commit()
    return {"status": "deleted", "id": preset_id}

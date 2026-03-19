from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    upload_id: str
    filename: str
    row_count: int
    headers: List[str]
    sample_rows: List[Dict[str, Any]]
    suggested_mapping: Dict[str, Optional[str]]
    target_fields: Dict[str, Dict[str, Any]]


class ColumnMappingRequest(BaseModel):
    upload_id: str
    data_type: str = Field(..., pattern="^(trading|production|weather)$")
    mapping: Dict[str, Optional[str]]  # {source_column: target_field_or_null}


class ImportPreviewResponse(BaseModel):
    upload_id: str
    total_rows: int
    valid_rows: int
    error_rows: int
    duplicate_rows: int
    errors: List[Dict[str, Any]]
    preview_data: List[Dict[str, Any]]


class ImportConfirmRequest(BaseModel):
    upload_id: str
    data_type: str = Field(..., pattern="^(trading|production|weather)$")
    skip_errors: bool = True


class ImportResultResponse(BaseModel):
    upload_id: str
    inserted: int
    skipped_duplicate: int
    skipped_error: int
    total_processed: int


class MappingPresetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    data_type: str = Field(..., pattern="^(trading|production|weather)$")
    mapping: Dict[str, Optional[str]]


class MappingPresetResponse(BaseModel):
    id: int
    name: str
    data_type: str
    mapping: Dict[str, Optional[str]]
    created_at: datetime

    model_config = {"from_attributes": True}

from __future__ import annotations

from email.parser import BytesParser
from email.policy import default
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db, get_request_id, require_module_roles
from app.api.errors import raise_api_error
from app.core.config import Settings
from app.domain.enums import ImportBatchStatus, ImportRowStatus, ModuleCode, ModuleRole
from app.models.user import User
from app.schemas.imports import (
    ImportBatchListResponse,
    ImportBatchRead,
    ImportRowListResponse,
)
from app.services.mfu_imports import (
    commit_import_batch,
    get_import_batch,
    list_import_batches,
    list_import_rows,
    upload_mfu_template,
)

router = APIRouter(prefix="/imports", tags=["imports"])

require_import_user = require_module_roles(ModuleCode.CAN_COMPLIANCE, ModuleRole.CAN_ADMIN, ModuleRole.CAN_OPS)


def _request_id(request: Request) -> str | None:
    return get_request_id(request)


def _parse_multipart_file(content_type: str, body: bytes) -> tuple[str, bytes] | None:
    raw_message = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    message = BytesParser(policy=default).parsebytes(raw_message)
    if not message.is_multipart():
        return None
    for part in message.iter_parts():
        file_name = part.get_filename()
        if not file_name:
            continue
        payload = part.get_payload(decode=True)
        return file_name, payload or b""
    return None


async def _read_upload(request: Request, file_name: str | None) -> tuple[str, bytes]:
    body = await request.body()
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        parsed = _parse_multipart_file(content_type, body)
        if parsed is None:
            raise_api_error(
                status.HTTP_400_BAD_REQUEST,
                "upload_file_required",
                "Multipart request must include a file field.",
            )
        return parsed

    resolved_file_name = file_name or request.headers.get("x-file-name")
    if not resolved_file_name:
        raise_api_error(
            status.HTTP_400_BAD_REQUEST,
            "file_name_required",
            "Raw uploads must provide file_name query parameter or X-File-Name header.",
        )
    return resolved_file_name, body


@router.post(
    "/mfu-template/upload",
    response_model=ImportBatchRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_mfu_template_file(
    request: Request,
    file_name: Annotated[str | None, Query()] = None,
    current_user: User = Depends(require_import_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    resolved_file_name, content = await _read_upload(request, file_name)
    return upload_mfu_template(
        db,
        file_name=resolved_file_name,
        content=content,
        actor=current_user,
        settings=settings,
    )


@router.get("", response_model=ImportBatchListResponse)
def list_import_batch_records(
    import_status: Annotated[ImportBatchStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    _current_user: User = Depends(require_import_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return list_import_batches(db, import_status=import_status, limit=limit, offset=offset)


@router.get("/{batch_id}", response_model=ImportBatchRead)
def get_import_batch_record(
    batch_id: UUID,
    _current_user: User = Depends(require_import_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return get_import_batch(db, batch_id=batch_id)


@router.get("/{batch_id}/rows", response_model=ImportRowListResponse)
def list_import_batch_row_records(
    batch_id: UUID,
    row_status: Annotated[ImportRowStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    _current_user: User = Depends(require_import_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return list_import_rows(
        db,
        batch_id=batch_id,
        row_status=row_status,
        limit=limit,
        offset=offset,
    )


@router.post("/{batch_id}/commit", response_model=ImportBatchRead)
def commit_import_batch_record(
    batch_id: UUID,
    request: Request,
    current_user: User = Depends(require_import_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    return commit_import_batch(
        db,
        batch_id=batch_id,
        actor=current_user,
        settings=settings,
        request_id=_request_id(request),
    )

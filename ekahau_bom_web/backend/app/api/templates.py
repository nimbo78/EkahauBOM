"""Batch template API endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.auth import verify_admin
from app.models import (
    BatchTemplate,
    TemplateCreateRequest,
    TemplateListItem,
    TemplateUpdateRequest,
)
from app.services.template_service import template_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateListItem])
async def list_templates(include_system: bool = True) -> list[TemplateListItem]:
    """List all templates.

    Args:
        include_system: Whether to include system templates (default: True)

    Returns:
        List of templates
    """
    templates = template_service.list_templates(include_system=include_system)

    return [
        TemplateListItem(
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            created_date=template.created_date,
            last_used=template.last_used,
            usage_count=template.usage_count,
            is_system=template.is_system,
        )
        for template in templates
    ]


@router.get("/{template_id}", response_model=BatchTemplate)
async def get_template(template_id: UUID) -> BatchTemplate:
    """Get template by ID.

    Args:
        template_id: Template UUID

    Returns:
        Template details

    Raises:
        HTTPException: If template not found
    """
    template = template_service.load_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.post("", response_model=BatchTemplate, dependencies=[Depends(verify_admin)])
async def create_template(request: TemplateCreateRequest) -> BatchTemplate:
    """Create a new template.

    Args:
        request: Template creation request

    Returns:
        Created template
    """
    template = template_service.create_template(request, created_by="admin")
    logger.info(f"Created template {template.template_id}: {template.name}")

    return template


@router.put("/{template_id}", response_model=BatchTemplate, dependencies=[Depends(verify_admin)])
async def update_template(template_id: UUID, request: TemplateUpdateRequest) -> BatchTemplate:
    """Update an existing template.

    Args:
        template_id: Template UUID
        request: Template update request

    Returns:
        Updated template

    Raises:
        HTTPException: If template not found or is a system template
    """
    try:
        template = template_service.update_template(template_id, request)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        logger.info(f"Updated template {template_id}: {template.name}")
        return template

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{template_id}", dependencies=[Depends(verify_admin)])
async def delete_template(template_id: UUID) -> dict:
    """Delete a template.

    Args:
        template_id: Template UUID

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If template not found or is a system template
    """
    try:
        success = template_service.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")

        logger.info(f"Deleted template {template_id}")
        return {"message": "Template deleted successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

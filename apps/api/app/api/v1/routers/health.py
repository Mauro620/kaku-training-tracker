"""Health check. Verifica que la base responda, no solo que el proceso viva."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter(tags=["health"])


class HealthRead(BaseModel):
    status: Literal["ok", "degraded"]
    base_de_datos: Literal["ok", "sin_conexion"]


@router.get(
    "/health",
    response_model=HealthRead,
    summary="Estado del servicio y de su base de datos",
)
async def leer_health(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HealthRead:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthRead(status="degraded", base_de_datos="sin_conexion")
    return HealthRead(status="ok", base_de_datos="ok")

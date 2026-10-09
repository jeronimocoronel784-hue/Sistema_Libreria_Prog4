"""Contratos del módulo health."""

from sqlmodel import SQLModel


class LiveRead(SQLModel):
    estado: str

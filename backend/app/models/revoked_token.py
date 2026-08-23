"""RevokedToken model"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class RevokedToken(SQLModel, table=True):
    """RevokedToken model"""

    __tablename__ = "revoked_tokens"
    jti: str = Field(primary_key=True, index=True)
    expires_at: datetime = Field(nullable=False)
    revoked_at: datetime = Field(default_factory=datetime.now, nullable=False)

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TurnFeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message_id: UUID
    type: str
    original: str
    corrected: str
    explanation: str
    severity: str
    created_at: datetime

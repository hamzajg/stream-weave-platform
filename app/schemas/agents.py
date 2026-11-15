# Agent schemas: conversations, messages, tool metadata.
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ConversationCreate(BaseModel):
    organization_id: UUID
    title: Optional[str] = Field(None, max_length=255)


class ConversationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: Optional[str]
    tool_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)


class MessageSendResponse(BaseModel):
    """Messages appended during one turn (user msg excluded)."""
    conversation_id: UUID
    messages: List[MessageResponse]


class ToolInfo(BaseModel):
    name: str
    description: str

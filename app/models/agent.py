"""Agent runtime models: conversations and messages."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.user import UUID


class AgentConversation(Base):
    """A chat session between a user and the org-scoped agent."""
    __tablename__ = "agent_conversations"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "AgentMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AgentMessage.created_at",
    )

    def __repr__(self):
        return f"<AgentConversation {self.id} org={self.organization_id}>"


class AgentMessage(Base):
    """A single message in an agent conversation.

    role: 'user' | 'assistant' | 'tool'
    For assistant messages that requested tool calls, `tool_calls` holds
    the raw JSON list so history can be replayed to the LLM faithfully.
    For tool messages, `tool_call_id`/`tool_name` link back to the call.
    """
    __tablename__ = "agent_messages"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID, ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=True)
    tool_calls = Column(Text, nullable=True)  # JSON list of tool calls
    tool_call_id = Column(String(100), nullable=True)
    tool_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("AgentConversation", back_populates="messages")

    def __repr__(self):
        return f"<AgentMessage {self.role} conv={self.conversation_id}>"

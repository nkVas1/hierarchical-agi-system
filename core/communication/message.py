"""Message definitions for inter-network communication."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(Enum):
    """Types of messages in the system."""

    # Query messages
    QUERY = "query"  # User query to process
    SUB_QUERY = "sub_query"  # Decomposed sub-query to network
    QUERY_RESPONSE = "query_response"  # Response to query

    # Control messages
    REGISTER = "register"  # Register new network
    UNREGISTER = "unregister"  # Unregister network
    HEARTBEAT = "heartbeat"  # Health check ping
    STATUS_UPDATE = "status_update"  # Network status update

    # Data messages
    DATA_REQUEST = "data_request"  # Request data from network
    DATA_RESPONSE = "data_response"  # Data response
    KNOWLEDGE_SHARE = "knowledge_share"  # Share knowledge between networks

    # Evolution messages
    PERFORMANCE_REPORT = "performance_report"  # Performance metrics
    QUALITY_ASSESSMENT = "quality_assessment"  # Quality evaluation
    REWARD_SIGNAL = "reward_signal"  # Reward/penalty signal
    PRUNING_NOTICE = "pruning_notice"  # Network will be removed

    # Innovation messages
    IDEA_PROPOSAL = "idea_proposal"  # New idea from innovation network
    HYPOTHESIS_TEST = "hypothesis_test"  # Test hypothesis request
    EXPERIMENT_RESULT = "experiment_result"  # Experiment results

    # Admin messages
    ADMIN_COMMAND = "admin_command"  # Command from administrator
    ADMIN_FEEDBACK = "admin_feedback"  # Feedback from master to admin
    SYSTEM_LOG = "system_log"  # System logging message


class MessagePriority(Enum):
    """Message priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Message:
    """Message for inter-network communication."""

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.QUERY
    sender_id: str = ""
    receiver_id: str = ""  # Empty string means broadcast
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_message_id: Optional[str] = None
    requires_response: bool = False
    timeout_seconds: float = 30.0
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "metadata": self.metadata,
            "parent_message_id": self.parent_message_id,
            "requires_response": self.requires_response,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            priority=MessagePriority(data["priority"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            payload=data["payload"],
            metadata=data.get("metadata", {}),
            parent_message_id=data.get("parent_message_id"),
            requires_response=data.get("requires_response", False),
            timeout_seconds=data.get("timeout_seconds", 30.0),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )

    def create_response(
        self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None
    ) -> "Message":
        """Create a response message to this message.

        Args:
            payload: Response payload
            metadata: Optional response metadata

        Returns:
            Response message
        """
        return Message(
            message_type=MessageType.QUERY_RESPONSE,
            sender_id=self.receiver_id,
            receiver_id=self.sender_id,
            priority=self.priority,
            payload=payload,
            metadata=metadata or {},
            parent_message_id=self.message_id,
        )

    def should_retry(self) -> bool:
        """Check if message should be retried."""
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1

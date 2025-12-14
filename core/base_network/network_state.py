"""Network state management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class StateType(Enum):
    """Network operational states."""

    INITIALIZING = "initializing"  # Network is starting up
    IDLE = "idle"  # Network is ready but not processing
    PROCESSING = "processing"  # Network is processing a query
    WAITING = "waiting"  # Waiting for sub-network responses
    ERROR = "error"  # Network encountered an error
    SHUTDOWN = "shutdown"  # Network is shutting down
    OFFLINE = "offline"  # Network is offline
    MAINTENANCE = "maintenance"  # Network is in maintenance mode


@dataclass
class NetworkState:
    """Current state of a neural network."""

    network_id: str
    state_type: StateType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    previous_state: Optional[StateType] = None
    error_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "network_id": self.network_id,
            "state_type": self.state_type.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "context": self.context,
            "previous_state": (
                self.previous_state.value if self.previous_state else None
            ),
            "error_info": self.error_info,
        }

    @property
    def is_operational(self) -> bool:
        """Check if network is in an operational state."""
        return self.state_type in {
            StateType.IDLE,
            StateType.PROCESSING,
            StateType.WAITING,
        }

    @property
    def is_available(self) -> bool:
        """Check if network can accept new queries."""
        return self.state_type == StateType.IDLE

    @property
    def requires_attention(self) -> bool:
        """Check if network requires human attention."""
        return self.state_type in {StateType.ERROR, StateType.MAINTENANCE}


class StateManager:
    """Manages state transitions for networks."""

    def __init__(self, network_id: str):
        """Initialize state manager.

        Args:
            network_id: ID of the network being managed
        """
        self.network_id = network_id
        self._current_state = NetworkState(
            network_id=network_id, state_type=StateType.OFFLINE
        )
        self._state_history: list[NetworkState] = []
        self._max_history = 100

    def transition_to(
        self,
        new_state: StateType,
        message: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> NetworkState:
        """Transition to a new state.

        Args:
            new_state: Target state
            message: Optional message describing the transition
            context: Optional context data

        Returns:
            New state object
        """
        # Store current state in history
        self._state_history.append(self._current_state)
        if len(self._state_history) > self._max_history:
            self._state_history.pop(0)

        # Create new state
        self._current_state = NetworkState(
            network_id=self.network_id,
            state_type=new_state,
            message=message,
            context=context or {},
            previous_state=self._current_state.state_type,
        )

        return self._current_state

    def set_error(
        self, message: str, error_info: Optional[Dict[str, Any]] = None
    ) -> NetworkState:
        """Set network to error state.

        Args:
            message: Error message
            error_info: Detailed error information

        Returns:
            Error state object
        """
        self._state_history.append(self._current_state)
        if len(self._state_history) > self._max_history:
            self._state_history.pop(0)

        self._current_state = NetworkState(
            network_id=self.network_id,
            state_type=StateType.ERROR,
            message=message,
            previous_state=self._current_state.state_type,
            error_info=error_info,
        )

        return self._current_state

    @property
    def current_state(self) -> NetworkState:
        """Get current state."""
        return self._current_state

    @property
    def state_history(self) -> list[NetworkState]:
        """Get state history."""
        return self._state_history.copy()

    def get_last_n_states(self, n: int) -> list[NetworkState]:
        """Get last n states from history.

        Args:
            n: Number of states to retrieve

        Returns:
            List of most recent states
        """
        return self._state_history[-n:] if n > 0 else []

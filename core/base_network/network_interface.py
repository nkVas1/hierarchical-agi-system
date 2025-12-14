"""Base network interface for all neural networks in the hierarchy."""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import structlog

logger = structlog.get_logger(__name__)


class NetworkType(Enum):
    """Types of networks in the hierarchy."""

    MASTER = "master"  # Master orchestrator
    DEPARTMENT = "department"  # Department-level coordinator
    SPECIALIST = "specialist"  # Specialized worker network
    INNOVATION = "innovation"  # Innovation/brainstorm network
    QUALITY_CONTROL = "quality_control"  # Quality monitoring network


@dataclass
class NetworkMetadata:
    """Metadata for a neural network."""

    network_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    network_type: NetworkType = NetworkType.SPECIALIST
    version: str = "0.1.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    parent_id: Optional[str] = None
    department: Optional[str] = None
    description: str = ""
    capabilities: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "network_id": self.network_id,
            "name": self.name,
            "network_type": self.network_type.value,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "parent_id": self.parent_id,
            "department": self.department,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "tags": list(self.tags),
        }


class BaseNetwork(ABC):
    """Abstract base class for all neural networks in the hierarchy.

    This class defines the interface that all networks must implement,
    ensuring consistent communication and management across the system.
    """

    def __init__(self, metadata: NetworkMetadata):
        """Initialize base network.

        Args:
            metadata: Network metadata including ID, type, and capabilities
        """
        self.metadata = metadata
        self.logger = structlog.get_logger(
            __name__, network_id=metadata.network_id, network_name=metadata.name
        )
        self._sub_networks: Dict[str, "BaseNetwork"] = {}
        self._is_active: bool = False
        self._performance_metrics: Dict[str, float] = {}
        self._request_count: int = 0
        self._error_count: int = 0
        self._last_active: Optional[datetime] = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the network and load any required resources.

        This method should set up the network's internal state,
        load models, establish connections, etc.
        """
        pass

    @abstractmethod
    async def process_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming query and return results.

        Args:
            query: Query data including type, parameters, and context

        Returns:
            Dictionary containing results, metadata, and status
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shutdown the network and release resources."""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get list of capabilities this network provides.

        Returns:
            List of capability identifiers
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status.

        Returns:
            Dictionary with health status, metrics, and diagnostics
        """
        pass

    # Common functionality for all networks

    def register_sub_network(self, network: "BaseNetwork") -> None:
        """Register a sub-network under this network's management.

        Args:
            network: Sub-network instance to register
        """
        self._sub_networks[network.metadata.network_id] = network
        network.metadata.parent_id = self.metadata.network_id
        self.logger.info(
            "sub_network_registered",
            sub_network_id=network.metadata.network_id,
            sub_network_name=network.metadata.name,
        )

    def unregister_sub_network(self, network_id: str) -> Optional["BaseNetwork"]:
        """Unregister and return a sub-network.

        Args:
            network_id: ID of the sub-network to unregister

        Returns:
            Unregistered network instance or None if not found
        """
        network = self._sub_networks.pop(network_id, None)
        if network:
            self.logger.info(
                "sub_network_unregistered",
                sub_network_id=network_id,
                reason="manual_unregister",
            )
        return network

    def get_sub_networks(self) -> List["BaseNetwork"]:
        """Get all registered sub-networks.

        Returns:
            List of sub-network instances
        """
        return list(self._sub_networks.values())

    def get_sub_network(self, network_id: str) -> Optional["BaseNetwork"]:
        """Get a specific sub-network by ID.

        Args:
            network_id: ID of the sub-network

        Returns:
            Sub-network instance or None if not found
        """
        return self._sub_networks.get(network_id)

    async def start(self) -> None:
        """Start the network and all its sub-networks."""
        try:
            await self.initialize()
            self._is_active = True
            self._last_active = datetime.utcnow()
            self.logger.info("network_started")

            # Start all sub-networks
            for sub_network in self._sub_networks.values():
                await sub_network.start()

        except Exception as e:
            self.logger.error("network_start_failed", error=str(e), exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop the network and all its sub-networks."""
        try:
            # Stop all sub-networks first
            for sub_network in self._sub_networks.values():
                await sub_network.stop()

            await self.shutdown()
            self._is_active = False
            self.logger.info("network_stopped")

        except Exception as e:
            self.logger.error("network_stop_failed", error=str(e), exc_info=True)
            raise

    def update_metrics(self, metrics: Dict[str, float]) -> None:
        """Update performance metrics.

        Args:
            metrics: Dictionary of metric names and values
        """
        self._performance_metrics.update(metrics)
        self.metadata.updated_at = datetime.utcnow()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics.

        Returns:
            Dictionary of metrics and statistics
        """
        return {
            "network_id": self.metadata.network_id,
            "name": self.metadata.name,
            "is_active": self._is_active,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": (
                self._error_count / self._request_count if self._request_count > 0 else 0
            ),
            "last_active": self._last_active.isoformat() if self._last_active else None,
            "performance_metrics": self._performance_metrics,
            "sub_networks_count": len(self._sub_networks),
        }

    def increment_request_count(self) -> None:
        """Increment the request counter."""
        self._request_count += 1
        self._last_active = datetime.utcnow()

    def increment_error_count(self) -> None:
        """Increment the error counter."""
        self._error_count += 1

    @property
    def is_active(self) -> bool:
        """Check if network is currently active."""
        return self._is_active

    @property
    def network_id(self) -> str:
        """Get network ID."""
        return self.metadata.network_id

    @property
    def network_name(self) -> str:
        """Get network name."""
        return self.metadata.name

    @property
    def network_type(self) -> NetworkType:
        """Get network type."""
        return self.metadata.network_type

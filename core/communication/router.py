"""Message routing for the hierarchical network system."""

import asyncio
from typing import Dict, List, Optional, Set

import structlog

from .message import Message, MessagePriority, MessageType
from .protocol import CommunicationProtocol

logger = structlog.get_logger(__name__)


class MessageRouter:
    """Routes messages between networks in the hierarchy."""

    def __init__(self):
        """Initialize message router."""
        self.logger = structlog.get_logger(__name__)

        # Network registry
        self._networks: Dict[str, CommunicationProtocol] = {}

        # Network capabilities
        self._network_capabilities: Dict[str, Set[str]] = {}

        # Message delivery tracking
        self._message_log: List[Dict] = []
        self._max_log_size = 10000

        # Priority queues
        self._priority_queues: Dict[MessagePriority, asyncio.Queue] = {
            priority: asyncio.Queue() for priority in MessagePriority
        }

        # Router task
        self._router_task: Optional[asyncio.Task] = None
        self._is_running = False

    def register_network(
        self, network_id: str, protocol: CommunicationProtocol, capabilities: Set[str]
    ) -> None:
        """Register a network with the router.

        Args:
            network_id: ID of the network
            protocol: Communication protocol instance
            capabilities: Set of capabilities the network provides
        """
        self._networks[network_id] = protocol
        self._network_capabilities[network_id] = capabilities
        self.logger.info(
            "network_registered",
            network_id=network_id,
            capabilities=list(capabilities),
        )

    def unregister_network(self, network_id: str) -> None:
        """Unregister a network from the router.

        Args:
            network_id: ID of the network to unregister
        """
        self._networks.pop(network_id, None)
        self._network_capabilities.pop(network_id, None)
        self.logger.info("network_unregistered", network_id=network_id)

    def find_networks_by_capability(self, capability: str) -> List[str]:
        """Find networks that provide a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of network IDs that provide the capability
        """
        return [
            network_id
            for network_id, caps in self._network_capabilities.items()
            if capability in caps
        ]

    async def route_message(self, message: Message) -> bool:
        """Route a message to its destination.

        Args:
            message: Message to route

        Returns:
            True if message was routed successfully
        """
        # Add to message log
        self._log_message(message)

        # Handle broadcast
        if not message.receiver_id:
            await self._broadcast(message)
            return True

        # Route to specific network
        protocol = self._networks.get(message.receiver_id)
        if not protocol:
            self.logger.warning(
                "receiver_not_found",
                message_id=message.message_id,
                receiver_id=message.receiver_id,
            )
            return False

        await protocol.receive_message(message)
        return True

    async def route_by_capability(
        self, message: Message, capability: str
    ) -> List[Message]:
        """Route message to networks with specific capability.

        Args:
            message: Message to route
            capability: Required capability

        Returns:
            List of response messages
        """
        network_ids = self.find_networks_by_capability(capability)

        if not network_ids:
            self.logger.warning(
                "no_networks_with_capability",
                capability=capability,
            )
            return []

        # Send to all capable networks
        tasks = []
        for network_id in network_ids:
            protocol = self._networks[network_id]
            msg = Message(
                message_type=message.message_type,
                sender_id=message.sender_id,
                receiver_id=network_id,
                priority=message.priority,
                payload=message.payload,
                metadata=message.metadata,
                parent_message_id=message.message_id,
                requires_response=True,
            )
            tasks.append(protocol.send_message(msg, wait_for_response=True))

        # Wait for all responses
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None and exceptions
        valid_responses = [
            r for r in responses if r is not None and not isinstance(r, Exception)
        ]

        return valid_responses

    async def _broadcast(self, message: Message) -> None:
        """Broadcast message to all networks.

        Args:
            message: Message to broadcast
        """
        tasks = []
        for network_id, protocol in self._networks.items():
            if network_id != message.sender_id:  # Don't send back to sender
                msg = Message(
                    message_type=message.message_type,
                    sender_id=message.sender_id,
                    receiver_id=network_id,
                    priority=message.priority,
                    payload=message.payload,
                    metadata=message.metadata,
                )
                tasks.append(protocol.receive_message(msg))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _log_message(self, message: Message) -> None:
        """Log message for tracking.

        Args:
            message: Message to log
        """
        self._message_log.append(message.to_dict())

        # Trim log if too large
        if len(self._message_log) > self._max_log_size:
            self._message_log = self._message_log[-self._max_log_size :]

    async def start(self) -> None:
        """Start the message router."""
        if self._is_running:
            return

        self._is_running = True
        self._router_task = asyncio.create_task(self._process_priority_queues())
        self.logger.info("router_started")

    async def stop(self) -> None:
        """Stop the message router."""
        if not self._is_running:
            return

        self._is_running = False

        if self._router_task:
            self._router_task.cancel()
            try:
                await self._router_task
            except asyncio.CancelledError:
                pass

        self.logger.info("router_stopped")

    async def _process_priority_queues(self) -> None:
        """Process messages from priority queues."""
        while self._is_running:
            try:
                # Process critical messages first
                for priority in sorted(
                    MessagePriority, key=lambda x: x.value, reverse=True
                ):
                    queue = self._priority_queues[priority]

                    try:
                        message = queue.get_nowait()
                        await self.route_message(message)
                    except asyncio.QueueEmpty:
                        continue

                # Small delay to prevent busy loop
                await asyncio.sleep(0.01)

            except Exception as e:
                self.logger.error(
                    "router_processing_error",
                    error=str(e),
                    exc_info=True,
                )

    def get_statistics(self) -> Dict:
        """Get router statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            "registered_networks": len(self._networks),
            "messages_logged": len(self._message_log),
            "is_running": self._is_running,
        }

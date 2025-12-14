"""Communication protocol for message exchange."""

import asyncio
from typing import Any, Callable, Dict, Optional, Set

import structlog

from .message import Message, MessageType

logger = structlog.get_logger(__name__)


class CommunicationProtocol:
    """Protocol for asynchronous message-based communication between networks."""

    def __init__(self, network_id: str):
        """Initialize communication protocol.

        Args:
            network_id: ID of the network using this protocol
        """
        self.network_id = network_id
        self.logger = structlog.get_logger(__name__, network_id=network_id)

        # Message handlers by message type
        self._handlers: Dict[MessageType, Callable] = {}

        # Pending responses
        self._pending_responses: Dict[str, asyncio.Future] = {}

        # Message queue
        self._message_queue: asyncio.Queue = asyncio.Queue()

        # Active connections
        self._connections: Set[str] = set()

        # Processing task
        self._processing_task: Optional[asyncio.Task] = None
        self._is_running = False

    def register_handler(
        self, message_type: MessageType, handler: Callable
    ) -> None:
        """Register a handler for a specific message type.

        Args:
            message_type: Type of message to handle
            handler: Async callable to handle the message
        """
        self._handlers[message_type] = handler
        self.logger.debug(
            "handler_registered",
            message_type=message_type.value,
        )

    async def send_message(
        self, message: Message, wait_for_response: bool = False
    ) -> Optional[Message]:
        """Send a message to another network.

        Args:
            message: Message to send
            wait_for_response: Whether to wait for a response

        Returns:
            Response message if wait_for_response is True, else None
        """
        message.sender_id = self.network_id

        self.logger.info(
            "sending_message",
            message_id=message.message_id,
            message_type=message.message_type.value,
            receiver_id=message.receiver_id,
            priority=message.priority.value,
        )

        # If waiting for response, create a future
        response_future = None
        if wait_for_response:
            response_future = asyncio.Future()
            self._pending_responses[message.message_id] = response_future
            message.requires_response = True

        # Put message in queue (simulated - in production, use message broker)
        await self._message_queue.put(message)

        # Wait for response if requested
        if response_future:
            try:
                response = await asyncio.wait_for(
                    response_future, timeout=message.timeout_seconds
                )
                return response
            except asyncio.TimeoutError:
                self.logger.warning(
                    "message_timeout",
                    message_id=message.message_id,
                )
                self._pending_responses.pop(message.message_id, None)

                # Retry if possible
                if message.should_retry():
                    message.increment_retry()
                    return await self.send_message(message, wait_for_response)

                return None

        return None

    async def receive_message(self, message: Message) -> None:
        """Receive and process an incoming message.

        Args:
            message: Received message
        """
        self.logger.info(
            "receiving_message",
            message_id=message.message_id,
            message_type=message.message_type.value,
            sender_id=message.sender_id,
        )

        # Check if this is a response to a pending request
        if (
            message.parent_message_id
            and message.parent_message_id in self._pending_responses
        ):
            future = self._pending_responses.pop(message.parent_message_id)
            if not future.done():
                future.set_result(message)
            return

        # Handle message based on type
        handler = self._handlers.get(message.message_type)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                self.logger.error(
                    "handler_error",
                    message_id=message.message_id,
                    message_type=message.message_type.value,
                    error=str(e),
                    exc_info=True,
                )
        else:
            self.logger.warning(
                "no_handler_found",
                message_type=message.message_type.value,
            )

    async def broadcast_message(self, message: Message) -> None:
        """Broadcast a message to all connected networks.

        Args:
            message: Message to broadcast
        """
        message.receiver_id = ""  # Empty means broadcast
        await self.send_message(message)

    async def start(self) -> None:
        """Start the communication protocol."""
        if self._is_running:
            return

        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_messages())
        self.logger.info("protocol_started")

    async def stop(self) -> None:
        """Stop the communication protocol."""
        if not self._is_running:
            return

        self._is_running = False

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        # Cancel all pending responses
        for future in self._pending_responses.values():
            if not future.done():
                future.cancel()

        self._pending_responses.clear()
        self.logger.info("protocol_stopped")

    async def _process_messages(self) -> None:
        """Process messages from the queue."""
        while self._is_running:
            try:
                # Get message from queue with timeout
                message = await asyncio.wait_for(
                    self._message_queue.get(), timeout=1.0
                )

                # In production, this would send to message broker
                # For now, just log
                self.logger.debug(
                    "message_processed",
                    message_id=message.message_id,
                )

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(
                    "processing_error",
                    error=str(e),
                    exc_info=True,
                )

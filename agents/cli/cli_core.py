"""
Core AgentCLI class with initialization and shared functionality.

This module contains the base AgentCLI class that serves as the central
coordinator for the CLI application.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.db import get_postgres_client
from agents.communication import Protocol, Conversation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agent_cli")


class AgentCLI:
    """
    Core of the command-line interface for testing agent interactions.

    This class serves as the central point of coordination for the CLI,
    maintaining state and providing access to the communication protocol.
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize the agent CLI.

        Args:
            db_url: Optional database URL (read from environment if not provided)
        """
        # Get database URL from environment if not provided
        self.db_url = db_url or os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory",
        )

        # Current conversation ID
        self.current_conversation_id: Optional[str] = None

        # Protocol instance (initialized on first use)
        self._protocol: Optional[Protocol] = None

        # Database client (initialized on first use)
        self._db_client = None

    @property
    def protocol(self) -> Protocol:
        """Get or create the protocol instance."""
        if self._protocol is None:
            # Initialize database client
            self._db_client = get_postgres_client(database_url=self.db_url)

            # Initialize protocol
            self._protocol = Protocol(
                db_client=self._db_client,
                validate_recipients=False,  # Allow unregistered agents for testing
            )

        return self._protocol

    @property
    def db_client(self):
        """Get or create the database client."""
        if self._db_client is None:
            self._db_client = get_postgres_client(database_url=self.db_url)
        return self._db_client

    async def close(self):
        """Clean up resources."""
        if self._db_client:
            await self._db_client.close()

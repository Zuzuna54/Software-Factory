# agents/orchestration/ceremonies.py

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from ..db.postgres import PostgresClient
from ..communication.protocol import CommunicationProtocol, MessageType


class AgileCeremonies:
    """
    Implementation of Agile ceremonies for structured team collaboration.
    """

    def __init__(self, db_client: PostgresClient, comm_protocol: CommunicationProtocol):
        self.db_client = db_client
        self.comm_protocol = comm_protocol
        self.logger = logging.getLogger("agent.ceremonies")

    async def initialize(self) -> None:
        """Initialize the ceremonies infrastructure."""
        # Create meetings table if it doesn't exist
        await self.db_client.execute(
            """
        CREATE TABLE IF NOT EXISTS meetings (
            meeting_id UUID PRIMARY KEY,
            meeting_type VARCHAR(50) NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            participants UUID[] NOT NULL,
            summary TEXT,
            decisions JSONB,
            action_items JSONB
        );
        """
        )

        # Create meeting conversations table
        await self.db_client.execute(
            """
        CREATE TABLE IF NOT EXISTS meeting_conversations (
            conversation_id UUID PRIMARY KEY,
            meeting_id UUID REFERENCES meetings(meeting_id),
            sequence_number INTEGER NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            speaker_id UUID NOT NULL,
            message TEXT NOT NULL,
            message_type VARCHAR(50),
            context JSONB
        );
        """
        )

        self.logger.info("Agile ceremonies infrastructure initialized")

    async def schedule_sprint_planning(
        self,
        scrum_master_id: str,
        product_manager_id: Optional[str],
        team_members: List[str],
        sprint_duration_days: int = 14,
        start_time: Optional[datetime] = None,
    ) -> str:
        """
        Schedule a sprint planning meeting.

        Args:
            scrum_master_id: ID of the Scrum Master agent
            product_manager_id: ID of the Product Manager agent (can be None)
            team_members: List of team member agent IDs
            sprint_duration_days: Duration of the sprint in days
            start_time: Start time for the meeting (defaults to now)

        Returns:
            The meeting ID
        """
        if start_time is None:
            start_time = datetime.now()

        meeting_id = str(uuid4())

        # Create meeting record
        query = """
        INSERT INTO meetings (
            meeting_id, meeting_type, start_time, participants
        )
        VALUES ($1, $2, $3, $4)
        """

        participants = [scrum_master_id]
        if product_manager_id:
            participants.append(product_manager_id)
        participants.extend(team_members)

        # Convert participant IDs to UUID objects for the query
        participant_uuids = [uuid4(p) for p in participants]

        await self.db_client.execute(
            query,
            uuid4(meeting_id),  # Ensure meeting_id is UUID
            "SprintPlanning",
            start_time,
            participant_uuids,  # Pass list of UUIDs
        )

        # Notify participants
        for agent_id in participants:
            # Create different messages for different roles
            if agent_id == scrum_master_id:
                content = f"Please facilitate the Sprint Planning meeting (ID: {meeting_id}) scheduled for {start_time}. You will lead the meeting and ensure all items are properly planned."
            elif agent_id == product_manager_id:
                content = f"Sprint Planning meeting (ID: {meeting_id}) scheduled for {start_time}. Please prepare the prioritized backlog items for planning."
            else:
                content = f"Sprint Planning meeting (ID: {meeting_id}) scheduled for {start_time}. Please prepare to discuss capacity and task assignments."

            # Send notification message
            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id,
                content=content,
                metadata={"meeting_id": meeting_id, "meeting_type": "SprintPlanning"},
            )

            # Store the notification message (Simulated)
            # await self.comm_protocol.send_message(notification) # Assuming send_message exists
            self.logger.info(
                f"Notification sent to {agent_id} about meeting {meeting_id}"
            )

        self.logger.info(
            f"Sprint Planning meeting {meeting_id} scheduled for {start_time}"
        )
        return meeting_id

    async def schedule_daily_standup(
        self,
        scrum_master_id: str,
        team_members: List[str],
        start_time: Optional[datetime] = None,
    ) -> str:
        """
        Schedule a daily standup meeting.

        Args:
            scrum_master_id: ID of the Scrum Master agent
            team_members: List of team member agent IDs
            start_time: Start time for the meeting (defaults to now)

        Returns:
            The meeting ID
        """
        if start_time is None:
            start_time = datetime.now()

        meeting_id = str(uuid4())

        # Create meeting record
        query = """
        INSERT INTO meetings (
            meeting_id, meeting_type, start_time, participants
        )
        VALUES ($1, $2, $3, $4)
        """

        participants = [scrum_master_id] + team_members
        participant_uuids = [uuid4(p) for p in participants]

        await self.db_client.execute(
            query, uuid4(meeting_id), "DailyStandup", start_time, participant_uuids
        )

        # Notify participants
        for agent_id in participants:
            if agent_id == scrum_master_id:
                content = f"Please facilitate the Daily Standup meeting (ID: {meeting_id}) scheduled for {start_time}."
            else:
                content = f"Daily Standup meeting (ID: {meeting_id}) scheduled for {start_time}. Please prepare updates on: 1) What you accomplished yesterday, 2) What you'll work on today, 3) Any blockers."

            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id,
                content=content,
                metadata={"meeting_id": meeting_id, "meeting_type": "DailyStandup"},
            )
            self.logger.info(
                f"Notification sent to {agent_id} about meeting {meeting_id}"
            )

        self.logger.info(
            f"Daily Standup meeting {meeting_id} scheduled for {start_time}"
        )
        return meeting_id

    async def schedule_sprint_review(
        self,
        scrum_master_id: str,
        product_manager_id: Optional[str],
        team_members: List[str],
        start_time: Optional[datetime] = None,
    ) -> str:
        """
        Schedule a sprint review meeting.

        Args:
            scrum_master_id: ID of the Scrum Master agent
            product_manager_id: ID of the Product Manager agent
            team_members: List of team member agent IDs
            start_time: Start time for the meeting (defaults to now)

        Returns:
            The meeting ID
        """
        if start_time is None:
            start_time = datetime.now()

        meeting_id = str(uuid4())

        query = """
        INSERT INTO meetings (
            meeting_id, meeting_type, start_time, participants
        )
        VALUES ($1, $2, $3, $4)
        """

        participants = [scrum_master_id]
        if product_manager_id:
            participants.append(product_manager_id)
        participants.extend(team_members)
        participant_uuids = [uuid4(p) for p in participants]

        await self.db_client.execute(
            query, uuid4(meeting_id), "SprintReview", start_time, participant_uuids
        )

        for agent_id in participants:
            if agent_id == scrum_master_id:
                content = f"Please facilitate the Sprint Review meeting (ID: {meeting_id}) scheduled for {start_time}."
            elif agent_id == product_manager_id:
                content = f"Sprint Review meeting (ID: {meeting_id}) scheduled for {start_time}. Please prepare to evaluate the completed work against acceptance criteria."
            else:
                content = f"Sprint Review meeting (ID: {meeting_id}) scheduled for {start_time}. Please prepare to demonstrate your completed work."

            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id,
                content=content,
                metadata={"meeting_id": meeting_id, "meeting_type": "SprintReview"},
            )
            self.logger.info(
                f"Notification sent to {agent_id} about meeting {meeting_id}"
            )

        self.logger.info(
            f"Sprint Review meeting {meeting_id} scheduled for {start_time}"
        )
        return meeting_id

    async def schedule_sprint_retrospective(
        self,
        scrum_master_id: str,
        team_members: List[str],
        start_time: Optional[datetime] = None,
    ) -> str:
        """
        Schedule a sprint retrospective meeting.

        Args:
            scrum_master_id: ID of the Scrum Master agent
            team_members: List of team member agent IDs
            start_time: Start time for the meeting (defaults to now)

        Returns:
            The meeting ID
        """
        if start_time is None:
            start_time = datetime.now()

        meeting_id = str(uuid4())

        query = """
        INSERT INTO meetings (
            meeting_id, meeting_type, start_time, participants
        )
        VALUES ($1, $2, $3, $4)
        """

        participants = [scrum_master_id] + team_members
        participant_uuids = [uuid4(p) for p in participants]

        await self.db_client.execute(
            query,
            uuid4(meeting_id),
            "SprintRetrospective",
            start_time,
            participant_uuids,
        )

        for agent_id in participants:
            if agent_id == scrum_master_id:
                content = f"Please facilitate the Sprint Retrospective meeting (ID: {meeting_id}) scheduled for {start_time}. Focus on what went well, what could be improved, and action items."
            else:
                content = f"Sprint Retrospective meeting (ID: {meeting_id}) scheduled for {start_time}. Please reflect on: 1) What went well, 2) What could be improved, 3) Action items for next sprint."

            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id,
                content=content,
                metadata={
                    "meeting_id": meeting_id,
                    "meeting_type": "SprintRetrospective",
                },
            )
            self.logger.info(
                f"Notification sent to {agent_id} about meeting {meeting_id}"
            )

        self.logger.info(
            f"Sprint Retrospective meeting {meeting_id} scheduled for {start_time}"
        )
        return meeting_id

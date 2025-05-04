# agents/orchestration/meetings.py

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from ..db.postgres import PostgresClient
from ..communication.protocol import CommunicationProtocol, MessageType, AgentMessage


class VirtualTeamMeetings:
    """
    Implementation of virtual team meetings for agent collaboration.
    """

    def __init__(self, db_client: PostgresClient, comm_protocol: CommunicationProtocol):
        self.db_client = db_client
        self.comm_protocol = comm_protocol
        self.logger = logging.getLogger("agent.meetings")
        self.active_meetings = (
            {}
        )  # Tracks currently active meetings: {meeting_id: {info}}

    async def start_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """
        Start a scheduled meeting.

        Args:
            meeting_id: ID of the meeting to start

        Returns:
            Meeting information
        """
        meeting_uuid = uuid4(meeting_id)
        # Get meeting information
        query = """
        SELECT meeting_type, participants, start_time
        FROM meetings
        WHERE meeting_id = $1
        """

        meeting_info_db = await self.db_client.fetch_one(query, meeting_uuid)

        if not meeting_info_db:
            error_msg = f"Meeting {meeting_id} not found"
            self.logger.error(error_msg)
            return {"error": error_msg}

        # Update meeting as in progress (use actual start time)
        update_query = """
        UPDATE meetings
        SET start_time = $1
        WHERE meeting_id = $2
        """

        actual_start_time = datetime.now()
        await self.db_client.execute(update_query, actual_start_time, meeting_uuid)

        # Convert participant UUIDs from DB back to strings
        participants_str = [str(p) for p in meeting_info_db["participants"]]

        # Mark meeting as active in memory
        self.active_meetings[meeting_id] = {
            "type": meeting_info_db["meeting_type"],
            "participants": participants_str,
            "start_time": actual_start_time,
            "messages": [],
        }

        # Notify participants that the meeting has started
        for agent_id_str in participants_str:
            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id_str,
                content=f"Meeting {meeting_id} ({meeting_info_db['meeting_type']}) has started.",
                metadata={
                    "meeting_id": meeting_id,
                    "meeting_type": meeting_info_db["meeting_type"],
                },
            )

            # Store the notification (Simulated)
            # await self.comm_protocol.send_message(notification)
            self.logger.info(
                f"Start notification sent to {agent_id_str} for meeting {meeting_id}"
            )

        self.logger.info(
            f"Meeting {meeting_id} ({meeting_info_db['meeting_type']}) started at {actual_start_time}"
        )

        return {
            "meeting_id": meeting_id,
            "type": meeting_info_db["meeting_type"],
            "start_time": actual_start_time,
            "participants": participants_str,
        }

    async def end_meeting(
        self,
        meeting_id: str,
        summary: Optional[str] = None,
        decisions: Optional[Dict[str, Any]] = None,
        action_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        End an active meeting and record outcomes.

        Args:
            meeting_id: ID of the meeting to end
            summary: Optional summary of the meeting
            decisions: Optional decisions made in the meeting
            action_items: Optional action items from the meeting

        Returns:
            Meeting outcome information
        """
        # Check if meeting is active
        if meeting_id not in self.active_meetings:
            error_msg = f"Meeting {meeting_id} is not active or already ended"
            # Check DB just in case it finished but wasn't cleared from memory (e.g. crash)
            db_meeting = await self.db_client.fetch_one(
                "SELECT end_time FROM meetings WHERE meeting_id = $1", uuid4(meeting_id)
            )
            if db_meeting and db_meeting["end_time"]:
                self.logger.warning(f"Meeting {meeting_id} was already ended in DB.")
                # Optionally return DB info or clear from memory if needed
            else:
                self.logger.error(error_msg)
                return {"error": error_msg}
            # If found in DB as ended, we might proceed to clear memory and return info
            # If not found or not ended in DB, it's a true error

        meeting_info = self.active_meetings.get(meeting_id)
        if not meeting_info:  # Should be caught above, but belt-and-suspenders
            error_msg = f"Meeting {meeting_id} not found in active meetings memory."
            self.logger.error(error_msg)
            return {"error": error_msg}

        meeting_uuid = uuid4(meeting_id)

        # Update meeting as completed in DB
        update_query = """
        UPDATE meetings
        SET end_time = $1, summary = $2, decisions = $3, action_items = $4
        WHERE meeting_id = $5
        """

        end_time = datetime.now()
        await self.db_client.execute(
            update_query,
            end_time,
            summary,
            json.dumps(decisions or {}),
            json.dumps(action_items or []),
            meeting_uuid,
        )

        # Remove from active meetings memory
        del self.active_meetings[meeting_id]

        # Notify participants that the meeting has ended
        for agent_id_str in meeting_info["participants"]:
            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id_str,
                content=f"Meeting {meeting_id} ({meeting_info['type']}) has ended.",
                metadata={
                    "meeting_id": meeting_id,
                    "meeting_type": meeting_info["type"],
                    "decisions_count": len(decisions or {}),
                    "action_items_count": len(action_items or []),
                },
            )

            # Store the notification (Simulated)
            # await self.comm_protocol.send_message(notification)
            self.logger.info(
                f"End notification sent to {agent_id_str} for meeting {meeting_id}"
            )

        self.logger.info(
            f"Meeting {meeting_id} ({meeting_info['type']}) ended at {end_time}"
        )

        return {
            "meeting_id": meeting_id,
            "type": meeting_info["type"],
            "start_time": meeting_info["start_time"],
            "end_time": end_time,
            "duration_minutes": (end_time - meeting_info["start_time"]).total_seconds()
            / 60,
            "summary": summary,
            "decisions": decisions,
            "action_items": action_items,
        }

    async def send_message_to_meeting(
        self,
        meeting_id: str,
        speaker_id: str,
        message: str,
        message_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message in an active meeting.

        Args:
            meeting_id: ID of the meeting
            speaker_id: ID of the agent sending the message
            message: Content of the message
            message_type: Optional type of message (Question, Answer, Proposal, etc.)
            context: Optional context information

        Returns:
            Information about the recorded message
        """
        # Check if meeting is active
        if meeting_id not in self.active_meetings:
            error_msg = f"Meeting {meeting_id} is not active"
            self.logger.error(error_msg)
            return {"error": error_msg}

        meeting_info = self.active_meetings[meeting_id]
        meeting_uuid = uuid4(meeting_id)
        speaker_uuid = uuid4(speaker_id)

        # Check if speaker is a participant
        if speaker_id not in meeting_info["participants"]:
            error_msg = (
                f"Agent {speaker_id} is not a participant in meeting {meeting_id}"
            )
            self.logger.error(error_msg)
            return {"error": error_msg}

        # Get current sequence number (using DB count for robustness)
        seq_query = "SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq FROM meeting_conversations WHERE meeting_id = $1"
        next_seq_result = await self.db_client.fetch_one(seq_query, meeting_uuid)
        sequence_number = next_seq_result["next_seq"]

        # Record the message in the database
        conversation_id = str(uuid4())
        timestamp = datetime.now()

        query = """
        INSERT INTO meeting_conversations (
            conversation_id, meeting_id, sequence_number,
            timestamp, speaker_id, message, message_type, context
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """

        await self.db_client.execute(
            query,
            uuid4(conversation_id),
            meeting_uuid,
            sequence_number,
            timestamp,
            speaker_uuid,
            message,
            message_type,
            json.dumps(context or {}),
        )

        # Update in-memory tracking (optional, could rely on DB)
        message_info = {
            "conversation_id": conversation_id,
            "sequence_number": sequence_number,
            "timestamp": timestamp,
            "speaker_id": speaker_id,
            "message": message,
            "message_type": message_type,
            "context": context,
        }
        # meeting_info["messages"].append(message_info) # Maybe remove if not needed

        # Broadcast to all participants
        for agent_id_str in meeting_info["participants"]:
            if agent_id_str != speaker_id:  # Don't send back to speaker
                notification = self.comm_protocol.create_inform(
                    sender=speaker_id,
                    receiver=agent_id_str,
                    content=message,
                    metadata={
                        "meeting_id": meeting_id,
                        "conversation_id": conversation_id,
                        "sequence_number": sequence_number,
                        "message_type": message_type,
                    },
                )

                # Store the notification (Simulated)
                # await self.comm_protocol.send_message(notification)
                self.logger.debug(f"Meeting message broadcast to {agent_id_str}")

        self.logger.info(
            f"Message recorded in meeting {meeting_id}: #{sequence_number} from {speaker_id}"
        )

        return message_info

    async def get_meeting_transcript(self, meeting_id: str) -> List[Dict[str, Any]]:
        """
        Get the transcript of a meeting.

        Args:
            meeting_id: ID of the meeting

        Returns:
            List of messages in sequence order
        """
        meeting_uuid = uuid4(meeting_id)
        query = """
        SELECT
            conversation_id, sequence_number, timestamp,
            speaker_id, message, message_type, context
        FROM meeting_conversations
        WHERE meeting_id = $1
        ORDER BY sequence_number
        """

        results = await self.db_client.fetch_all(query, meeting_uuid)

        transcript = []
        for row in results:
            transcript.append(
                {
                    "conversation_id": str(row["conversation_id"]),
                    "sequence_number": row["sequence_number"],
                    "timestamp": row["timestamp"],
                    "speaker_id": str(row["speaker_id"]),
                    "message": row["message"],
                    "message_type": row["message_type"],
                    "context": json.loads(row["context"]) if row["context"] else {},
                }
            )

        self.logger.info(
            f"Retrieved transcript for meeting {meeting_id}: {len(transcript)} messages"
        )
        return transcript

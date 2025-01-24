from typing import Any, Dict, List, Optional

from autogen_core.base import AgentId
from autogen_core.base.intervention import DefaultInterventionHandler

from src.backend.models.messages import GroupChatMessage

from src.backend.models.messages import GetHumanInputMessage


class NeedsUserInputHandler(DefaultInterventionHandler):
    def __init__(self):
        self.question_for_human: Optional[GetHumanInputMessage] = None
        self.messages: List[Dict[str, Any]] = []

    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any:
        sender_type = sender.type if sender else "unknown_type"
        sender_key = sender.key if sender else "unknown_key"
        print(
            f"NeedsUserInputHandler received message: {message} from sender: {sender}"
        )
        if isinstance(message, GetHumanInputMessage):
            self.question_for_human = message
            self.messages.append(
                {
                    "agent": {"type": sender_type, "key": sender_key},
                    "content": message.content,
                }
            )
            print("Captured question for human in NeedsUserInputHandler")
        elif isinstance(message, GroupChatMessage):
            self.messages.append(
                {
                    "agent": {"type": sender_type, "key": sender_key},
                    "content": message.body.content,
                }
            )
            print(f"Captured group chat message in NeedsUserInputHandler - {message}")
        return message

    @property
    def needs_human_input(self) -> bool:
        return self.question_for_human is not None

    @property
    def question_content(self) -> Optional[str]:
        if self.question_for_human:
            return self.question_for_human.content
        return None

    def get_messages(self) -> List[Dict[str, Any]]:
        messages = self.messages.copy()
        self.messages.clear()
        print("Returning and clearing captured messages in NeedsUserInputHandler")
        return messages


class AssistantResponseHandler(DefaultInterventionHandler):
    def __init__(self):
        self.assistant_response: Optional[str] = None

    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any:
        # Check if the message is from the assistant agent
        print(
            f"on_publish called in AssistantResponseHandler with message from sender: {sender} - {message}"
        )
        if hasattr(message, "body") and sender and sender.type in ["writer", "editor"]:
            self.assistant_response = message.body.content
            print("Assistant response set in AssistantResponseHandler")
        return message

    @property
    def has_response(self) -> bool:
        has_response = self.assistant_response is not None
        print(f"has_response called, returning: {has_response}")
        return has_response

    def get_response(self) -> Optional[str]:
        response = self.assistant_response
        print(f"get_response called, returning: {response}")
        return response

from typing import Any, Dict, List, Optional

import semantic_kernel as sk
from semantic_kernel.kernel_pydantic import KernelBaseModel


# Define message classes directly in this file since the imports are problematic
class GetHumanInputMessage(KernelBaseModel):
    """Message requesting input from a human."""

    content: str


class MessageBody(KernelBaseModel):
    """Simple message body class with content."""

    content: str


class GroupChatMessage(KernelBaseModel):
    """Message in a group chat."""

    body: Any
    source: str
    session_id: str
    target: str = ""

    def __str__(self):
        content = self.body.content if hasattr(self.body, "content") else str(self.body)
        return f"GroupChatMessage(source={self.source}, content={content})"


class NeedsUserInputHandler:
    """Handler for capturing messages that need human input."""

    def __init__(self):
        self.question_for_human: Optional[GetHumanInputMessage] = None
        self.messages: List[Dict[str, Any]] = []

    async def on_message(
        self,
        message: Any,
        sender_type: str = "unknown_type",
        sender_key: str = "unknown_key",
    ) -> Any:
        """Process an incoming message.

        This is equivalent to the on_publish method in the original version.

        Args:
            message: The message to process
            sender_type: The type of the sender (equivalent to sender.type in previous)
            sender_key: The key of the sender (equivalent to sender.key in previous)

        Returns:
            The original message (for pass-through functionality)
        """
        print(
            f"NeedsUserInputHandler received message: {message} from sender: {sender_type}/{sender_key}"
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
            # Ensure we extract content consistently with the original implementation
            content = (
                message.body.content
                if hasattr(message.body, "content")
                else str(message.body)
            )
            self.messages.append(
                {
                    "agent": {"type": sender_type, "key": sender_key},
                    "content": content,
                }
            )
            print(f"Captured group chat message in NeedsUserInputHandler - {message}")
        elif isinstance(message, dict) and "content" in message:
            # Handle messages directly from AzureAIAgent
            self.question_for_human = GetHumanInputMessage(content=message["content"])
            self.messages.append(
                {
                    "agent": {"type": sender_type, "key": sender_key},
                    "content": message["content"],
                }
            )
            print("Captured question from AzureAIAgent in NeedsUserInputHandler")

        return message

    @property
    def needs_human_input(self) -> bool:
        """Check if human input is needed."""
        return self.question_for_human is not None

    @property
    def question_content(self) -> Optional[str]:
        """Get the content of the question for human."""
        if self.question_for_human:
            return self.question_for_human.content
        return None

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get captured messages and clear buffer."""
        messages = self.messages.copy()
        self.messages.clear()
        print("Returning and clearing captured messages in NeedsUserInputHandler")
        return messages


class AssistantResponseHandler:
    """Handler for capturing assistant responses."""

    def __init__(self):
        self.assistant_response: Optional[str] = None

    async def on_message(self, message: Any, sender_type: str = None) -> Any:
        """Process an incoming message from an assistant.

        This is equivalent to the on_publish method in the original version.

        Args:
            message: The message to process
            sender_type: The type of the sender (equivalent to sender.type in previous)

        Returns:
            The original message (for pass-through functionality)
        """
        print(
            f"on_message called in AssistantResponseHandler with message from sender: {sender_type} - {message}"
        )

        if hasattr(message, "body") and sender_type in ["writer", "editor"]:
            # Ensure we're handling the content consistently with the original implementation
            self.assistant_response = (
                message.body.content
                if hasattr(message.body, "content")
                else str(message.body)
            )
            print("Assistant response set in AssistantResponseHandler")
        elif isinstance(message, dict) and "value" in message and sender_type:
            # Handle message from AzureAIAgent
            self.assistant_response = message["value"]
            print(
                "Assistant response from AzureAIAgent set in AssistantResponseHandler"
            )

        return message

    @property
    def has_response(self) -> bool:
        """Check if response is available."""
        has_response = self.assistant_response is not None
        print(f"has_response called, returning: {has_response}")
        return has_response

    def get_response(self) -> Optional[str]:
        """Get captured response."""
        response = self.assistant_response
        print(f"get_response called, returning: {response}")
        return response


# Helper function to register handlers with a Semantic Kernel instance
def register_handlers(kernel: sk.Kernel, session_id: str) -> tuple:
    """Register interrupt handlers with a Semantic Kernel instance.

    This is a new function that provides Semantic Kernel integration.

    Args:
        kernel: The Semantic Kernel instance
        session_id: The session identifier

    Returns:
        Tuple of (NeedsUserInputHandler, AssistantResponseHandler)
    """
    user_input_handler = NeedsUserInputHandler()
    assistant_handler = AssistantResponseHandler()

    # Create kernel functions for the handlers
    kernel.add_function(
        user_input_handler.on_message,
        plugin_name=f"user_input_handler_{session_id}",
        function_name="on_message",
    )

    kernel.add_function(
        assistant_handler.on_message,
        plugin_name=f"assistant_handler_{session_id}",
        function_name="on_message",
    )

    # Store handler references in kernel's context variables for later retrieval
    kernel.set_variable(f"input_handler_{session_id}", user_input_handler)
    kernel.set_variable(f"response_handler_{session_id}", assistant_handler)

    print(f"Registered handlers for session {session_id} with kernel")
    return user_input_handler, assistant_handler


# Helper function to get the registered handlers for a session
def get_handlers(kernel: sk.Kernel, session_id: str) -> tuple:
    """Get the registered interrupt handlers for a session.

    This is a new function that provides Semantic Kernel integration.

    Args:
        kernel: The Semantic Kernel instance
        session_id: The session identifier

    Returns:
        Tuple of (NeedsUserInputHandler, AssistantResponseHandler)
    """
    user_input_handler = kernel.get_variable(f"input_handler_{session_id}", None)
    assistant_handler = kernel.get_variable(f"response_handler_{session_id}", None)

    # Create new handlers if they don't exist
    if not user_input_handler or not assistant_handler:
        return register_handlers(kernel, session_id)

    return user_input_handler, assistant_handler

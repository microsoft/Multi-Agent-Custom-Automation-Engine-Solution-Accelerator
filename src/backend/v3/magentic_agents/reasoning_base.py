"""
Base agent classes and custom implementations for employee onboarding system.
"""

from semantic_kernel.agents import ChatCompletionAgent # pylint: disable=no-name-in-module
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior

class CustomReasoningAgent(ChatCompletionAgent):
    """Custom Semantic Kernel agent with o3 reasoning model and MCP access."""
    
    def __init__(
        self, 
        kernel: Kernel, 
        name: str = "ReasoningAgent",
        description: str = "An intelligent reasoning assistant powered by o3 model with MCP access",
        instructions: str = "",
        function_choice_behavior = None
    ):
        # Get the chat completion service from the kernel
        chat_service = kernel.get_service(type=AzureChatCompletion)
        
        # Initialize the base ChatCompletionAgent class
        super().__init__(
            kernel=kernel,
            service=chat_service,
            name=name,
            description=description,
            instructions=instructions,
            function_choice_behavior=function_choice_behavior
        )

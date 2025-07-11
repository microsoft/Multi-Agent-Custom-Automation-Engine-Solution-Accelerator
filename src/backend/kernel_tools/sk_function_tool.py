from typing import Any
from azure.ai.agents.models import ToolDefinition
from semantic_kernel import Kernel

class SKFunctionTool(ToolDefinition):
    def __init__(self, plugin_name: str, function_name: str, kernel: Kernel):
        self.plugin_name = plugin_name
        self.function_name = function_name
        self.kernel = kernel

    @property
    def input_schema(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            },
            "required": ["input"]
        }

    @property
    def output_schema(self):
        return {"type": "string"}

    async def invoke(self, input_data: dict[str, Any]) -> Any:
        sk_func = self.kernel.get_function(self.plugin_name, self.function_name)
        return await sk_func.invoke_async(input_data["input"])

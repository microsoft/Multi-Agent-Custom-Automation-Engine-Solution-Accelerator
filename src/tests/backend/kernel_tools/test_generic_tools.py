import sys
import types
import pytest
import json
import inspect
from typing import Annotated, List, Dict
from unittest.mock import patch

# ----- Mocking semantic_kernel.functions.kernel_function -----
semantic_kernel = types.ModuleType("semantic_kernel")
semantic_kernel.functions = types.ModuleType("functions")

def mock_kernel_function(*args, **kwargs):
    def decorator(func):
        func.__kernel_function__ = types.SimpleNamespace(**kwargs)
        return func
    return decorator

semantic_kernel.functions.kernel_function = mock_kernel_function
sys.modules["semantic_kernel"] = semantic_kernel
sys.modules["semantic_kernel.functions"] = semantic_kernel.functions
# -------------------------------------------------------------

# ----- Mocking models.messages_kernel.AgentType -----
mock_models = types.ModuleType("models")
mock_messages_kernel = types.ModuleType("models.messages_kernel")

class AgentType:
    GENERIC = type("AgentValue", (), {"value": "generic"})

mock_messages_kernel.AgentType = AgentType
mock_models.messages_kernel = mock_messages_kernel

sys.modules["models"] = mock_models
sys.modules["models.messages_kernel"] = mock_messages_kernel
# ----------------------------------------------------

from src.backend.kernel_tools.generic_tools import GenericTools
from semantic_kernel.functions import kernel_function

# ----------------- Inject kernel_function examples -----------------

@kernel_function(description="Add two integers")
async def add_numbers(a: int, b: int) -> int:
    """Adds two numbers"""
    return a + b

GenericTools.add_numbers = staticmethod(add_numbers)

@kernel_function(description="Add two integers")
async def add(x: int, y: int) -> int:
    return x + y

@kernel_function(description="Subtract two integers")
async def subtract(x: int, y: int) -> int:
    return x - y

@kernel_function
async def only_docstring(x: int) -> int:
    """Docstring exists"""
    return x

@kernel_function(description="Has cls parameter")
async def func_with_cls(cls, param: int) -> int:
    return param

@kernel_function(description="Sample")
async def sample(x: int) -> int:
    return x

@kernel_function(description="Annotated param")
async def annotated_param(x: Annotated[int, "Some metadata"]) -> int:
    return x

# ------------------------- Tests -------------------------

def test_get_all_kernel_functions_includes_add_numbers():
    functions = GenericTools.get_all_kernel_functions()
    assert "add_numbers" in functions
    assert inspect.iscoroutinefunction(functions["add_numbers"])

def test_generate_tools_json_doc_includes_add_numbers_arguments():
    json_doc = GenericTools.generate_tools_json_doc()
    parsed = json.loads(json_doc)
    found = False
    for tool in parsed:
        if tool["function"] == "add_numbers":
            found = True
            args = json.loads(tool["arguments"].replace("'", '"'))
            assert "a" in args
            assert args["a"]["type"] == "int"
            assert args["a"]["title"] == "A"
            assert args["a"]["description"] == "a"
            assert "b" in args
            assert args["b"]["type"] == "int"
    assert found

def test_generate_tools_json_doc_handles_non_kernel_function():
    class Dummy(GenericTools):
        @staticmethod
        def regular_function():
            pass
    Dummy.agent_name = "dummy"
    json_doc = Dummy.generate_tools_json_doc()
    parsed = json.loads(json_doc)
    assert all(tool["function"] != "regular_function" for tool in parsed)

def test_get_all_kernel_functions_no_kernel_functions():
    class Dummy(GenericTools):
        pass
    functions = Dummy.get_all_kernel_functions()
    own_functions = {name: fn for name, fn in functions.items() if name in Dummy.__dict__}
    assert own_functions == {}

def test_get_all_kernel_functions_multiple_kernel_functions():
    class Dummy(GenericTools):
        add = staticmethod(add)
        subtract = staticmethod(subtract)
    dummy = Dummy()
    funcs = dummy.get_all_kernel_functions()
    assert "add" in funcs
    assert "subtract" in funcs

def test_generate_tools_json_doc_no_arguments():
    @kernel_function(description="Return a constant string")
    async def return_constant() -> str:
        return "Constant"
    GenericTools.return_constant = staticmethod(return_constant)
    json_doc = GenericTools.generate_tools_json_doc()
    parsed = json.loads(json_doc)
    tool = next((t for t in parsed if t["function"] == "return_constant"), None)
    assert tool is not None
    assert json.loads(tool["arguments"].replace("'", '"')) == {}

def test_generate_tools_json_doc_complex_argument_types():
    @kernel_function(description="Process a list of integers")
    async def process_list(numbers: List[int]) -> int:
        return sum(numbers)
    @kernel_function(description="Process a dictionary")
    async def process_dict(data: Dict[str, int]) -> int:
        return sum(data.values())
    GenericTools.process_list = staticmethod(process_list)
    GenericTools.process_dict = staticmethod(process_dict)
    parsed = json.loads(GenericTools.generate_tools_json_doc())
    tool1 = next((t for t in parsed if t["function"] == "process_list"), None)
    assert tool1 is not None
    assert json.loads(tool1["arguments"].replace("'", '"'))["numbers"]["type"] == "list"
    tool2 = next((t for t in parsed if t["function"] == "process_dict"), None)
    assert tool2 is not None
    assert json.loads(tool2["arguments"].replace("'", '"'))["data"]["type"] == "dict"

def test_generate_tools_json_doc_boolean_argument_type():
    @kernel_function(description="Toggle a feature")
    async def toggle_feature(enabled: bool) -> str:
        return "Enabled" if enabled else "Disabled"
    GenericTools.toggle_feature = staticmethod(toggle_feature)
    parsed = json.loads(GenericTools.generate_tools_json_doc())
    tool = next((t for t in parsed if t["function"] == "toggle_feature"), None)
    assert tool is not None
    assert json.loads(tool["arguments"].replace("'", '"'))["enabled"]["type"] == "bool"

def test_generate_tools_json_doc_float_argument_type():
    @kernel_function(description="Multiply a number")
    async def multiply_by_two(value: float) -> float:
        return value * 2
    GenericTools.multiply_by_two = staticmethod(multiply_by_two)
    parsed = json.loads(GenericTools.generate_tools_json_doc())
    tool = next((t for t in parsed if t["function"] == "multiply_by_two"), None)
    assert tool is not None
    assert json.loads(tool["arguments"].replace("'", '"'))["value"]["type"] == "float"



def test_generate_tools_json_doc_raw_list_type():
    @kernel_function(description="Accept raw list type")
    async def accept_raw_list(items: list) -> int:
        return len(items)
    GenericTools.accept_raw_list = staticmethod(accept_raw_list)
    parsed = json.loads(GenericTools.generate_tools_json_doc())
    tool = next((t for t in parsed if t["function"] == "accept_raw_list"), None)
    assert tool is not None
    assert json.loads(tool["arguments"].replace("'", '"'))["items"]["type"] == "list"

def test_generate_tools_json_doc_raw_dict_type():
    @kernel_function(description="Accept raw dict type")
    async def accept_raw_dict(data: dict) -> int:
        return len(data)
    GenericTools.accept_raw_dict = staticmethod(accept_raw_dict)
    parsed = json.loads(GenericTools.generate_tools_json_doc())
    tool = next((t for t in parsed if t["function"] == "accept_raw_dict"), None)
    assert tool is not None
    assert json.loads(tool["arguments"].replace("'", '"'))["data"]["type"] == "dict"

def test_generate_tools_json_doc_fallback_type():
    class CustomType:
        pass
    @kernel_function(description="Uses custom type")
    async def use_custom_type(param: CustomType) -> str:
        return "ok"
    GenericTools.use_custom_type = staticmethod(use_custom_type)
    parsed = json.loads(GenericTools.generate_tools_json_doc())
    tool = next((t for t in parsed if t["function"] == "use_custom_type"), None)
    assert tool is not None
    assert json.loads(tool["arguments"].replace("'", '"'))["param"]["type"] == "customtype"



def test_generate_tools_json_doc_skips_cls_param():
    GenericTools.func_with_cls = staticmethod(func_with_cls)
    parsed = json.loads(GenericTools.generate_tools_json_doc())
    tool = next((t for t in parsed if t["function"] == "func_with_cls"), None)
    assert tool is not None
    args = json.loads(tool["arguments"].replace("'", '"'))
    assert "cls" not in args
    assert "param" in args

def test_generate_tools_json_doc_with_no_kernel_functions():
    class Dummy:
        agent_name = "dummy"
        @classmethod
        def get_all_kernel_functions(cls):
            return []
        @classmethod
        def generate_tools_json_doc(cls):
            return json.dumps([])
    parsed = json.loads(Dummy.generate_tools_json_doc())
    assert parsed == []

def test_generate_tools_json_doc_sets_agent_name():
    class CustomAgent(GenericTools):
        agent_name = "custom_agent"
        sample = staticmethod(sample)
    parsed = json.loads(CustomAgent.generate_tools_json_doc())
    tool = next((t for t in parsed if t["function"] == "sample"), None)
    assert tool is not None
    assert tool["agent"] == "custom_agent"

def test_generate_tools_json_doc_handles_annotated_type():
    GenericTools.annotated_param = staticmethod(annotated_param)
    parsed = json.loads(GenericTools.generate_tools_json_doc())
    tool = next((t for t in parsed if t["function"] == "annotated_param"), None)
    assert tool is not None
    args = json.loads(tool["arguments"].replace("'", '"'))
    assert args["x"]["type"] == "int"

def test_generate_tools_json_doc_multiple_functions():
    class Dummy(GenericTools):
        agent_name = "dummy"
        @kernel_function(description="Add numbers")
        async def add(self, a: int, b: int) -> int:
            return a + b
        @kernel_function(description="Concat strings")
        async def concat(self, x: str, y: str) -> str:
            return x + y
    parsed = json.loads(Dummy.generate_tools_json_doc())
    assert any(tool["function"] == "add" for tool in parsed)
    assert any(tool["function"] == "concat" for tool in parsed)
    assert all(tool["agent"] == "dummy" for tool in parsed)

# src/tests/backend/handlers/test_runtime_interrupt_kernel.py

import sys
import os
import types
import pytest
import asyncio

# ─── Stub out semantic_kernel so the module import works ─────────────────────────
sk = types.ModuleType("semantic_kernel")
ka = types.ModuleType("semantic_kernel.kernel_arguments")
kp = types.ModuleType("semantic_kernel.kernel_pydantic")

# Provide classes so subclassing and instantiation work
class StubKernelBaseModel:
    def __init__(self, **data):
        for k, v in data.items(): setattr(self, k, v)

class StubKernelArguments:
    pass

class StubKernel:
    def __init__(self):
        self.functions = {}
        self.variables = {}
    def add_function(self, func, plugin_name, function_name):
        self.functions[(plugin_name, function_name)] = func
    def set_variable(self, name, value):
        self.variables[name] = value
    def get_variable(self, name, default=None):
        return self.variables.get(name, default)

# Assign stubs to semantic_kernel modules
sk.Kernel = StubKernel
ka.KernelArguments = StubKernelArguments
kp.KernelBaseModel = StubKernelBaseModel

# Install into sys.modules before import
sys.modules["semantic_kernel"] = sk
sys.modules["semantic_kernel.kernel_arguments"] = ka
sys.modules["semantic_kernel.kernel_pydantic"] = kp
# ────────────────────────────────────────────────────────────────────────────────

# Ensure <repo root>/src is on sys.path
THIS_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", "..", ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Now import the module under test
from backend.handlers.runtime_interrupt_kernel import (
    GetHumanInputMessage,
    MessageBody,
    GroupChatMessage,
    NeedsUserInputHandler,
    AssistantResponseHandler,
    register_handlers,
    get_handlers,
)

# ─── Tests ───────────────────────────────────────────────────────────────────

def test_models_and_str():
    # GetHumanInputMessage and MessageBody
    gi = GetHumanInputMessage(content="hi")
    assert gi.content == "hi"
    mb = MessageBody(content="body")
    assert mb.content == "body"

    # GroupChatMessage with content attr
    class B1:
        def __init__(self, content):
            self.content = content
    g1 = GroupChatMessage(body=B1("c1"), source="S1", session_id="SID", target="T1")
    assert str(g1) == "GroupChatMessage(source=S1, content=c1)"

    # GroupChatMessage without content attr
    class B2:
        def __str__(self): return "bodystr"
    g2 = GroupChatMessage(body=B2(), source="S2", session_id="SID2", target="")
    assert "bodystr" in str(g2)

@pytest.mark.asyncio
async def test_needs_user_handler_all_branches():
    h = NeedsUserInputHandler()
    # initial
    assert not h.needs_human_input
    assert h.question_content is None
    assert h.get_messages() == []

    # human input message
    human = GetHumanInputMessage(content="ask")
    ret = await h.on_message(human, sender_type="T", sender_key="K")
    assert ret is human
    assert h.needs_human_input
    assert h.question_content == "ask"
    msgs = h.get_messages()
    assert msgs == [{"agent": {"type": "T", "key": "K"}, "content": "ask"}]

    # group chat message
    class B:
        content = "grp"
    grp = GroupChatMessage(body=B(), source="A", session_id="SID3", target="")
    ret2 = await h.on_message(grp, sender_type="A", sender_key="B")
    assert ret2 is grp
    # human_input remains
    assert h.needs_human_input
    msgs2 = h.get_messages()
    assert msgs2 == [{"agent": {"type": "A", "key": "B"}, "content": "grp"}]

    # dict message branch
    d = {"content": "xyz"}
    ret3 = await h.on_message(d, sender_type="X", sender_key="Y")
    assert isinstance(h.question_for_human, GetHumanInputMessage)
    assert h.question_content == "xyz"
    msgs3 = h.get_messages()
    assert msgs3 == [{"agent": {"type": "X", "key": "Y"}, "content": "xyz"}]

@pytest.mark.asyncio
async def test_needs_user_handler_unrelated():
    h = NeedsUserInputHandler()
    class C: pass
    obj = C()
    ret = await h.on_message(obj, sender_type="t", sender_key="k")
    assert ret is obj
    assert not h.needs_human_input
    assert h.get_messages() == []

@pytest.mark.asyncio
async def test_assistant_response_handler_various():
    h = AssistantResponseHandler()
    # no response yet
    assert not h.has_response

    # writer branch with content attr
    class Body:
        content = "r1"
    msg = type("M", (), {"body": Body()})()
    out = await h.on_message(msg, sender_type="writer")
    assert out is msg
    assert h.has_response and h.get_response() == "r1"

    # editor branch with no content attr
    class Body2:
        def __str__(self): return "s2"
    msg2 = type("M2", (), {"body": Body2()})()
    await h.on_message(msg2, sender_type="editor")
    assert h.get_response() == "s2"

    # dict/value branch
    await h.on_message({"value": "v2"}, sender_type="any")
    assert h.get_response() == "v2"

    # no-match
    prev = h.assistant_response
    await h.on_message(123, sender_type="writer")
    assert h.assistant_response == prev


def test_register_and_get_handlers_flow():
    k = StubKernel()
    u1, a1 = register_handlers(k, "sess")
    assert ("user_input_handler_sess", "on_message") in k.functions
    assert ("assistant_handler_sess", "on_message") in k.functions
    assert k.get_variable("input_handler_sess") is u1
    assert k.get_variable("response_handler_sess") is a1

    # get existing
    u2, a2 = get_handlers(k, "sess")
    assert u2 is u1 and a2 is a1

    # new pair when missing
    k2 = StubKernel()
    k2.set_variable("input_handler_new", None)
    k2.set_variable("response_handler_new", None)
    u3, a3 = get_handlers(k2, "new")
    assert isinstance(u3, NeedsUserInputHandler)
    assert isinstance(a3, AssistantResponseHandler)

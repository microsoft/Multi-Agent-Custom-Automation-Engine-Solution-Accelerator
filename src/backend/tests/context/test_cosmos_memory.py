import os
import sys
import asyncio
import pytest

# Adjust sys.path so that the project root is found.
# Test file location: src/backend/tests/context/test_cosmos_memory.py
# Project root is three levels up.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Set required environment variables before importing modules that depend on them.
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"


from src.backend.context.cosmos_memory import CosmosBufferedChatCompletionContext
from src.backend.models.messages import BaseDataModel


# --- DummyModel for Testing ---
class DummyModel(BaseDataModel):
    id: str
    session_id: str
    data_type: str
    user_id: str

    def model_dump(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "data_type": self.data_type,
            "user_id": self.user_id,
        }

    @classmethod
    def model_validate(cls, data):
        return DummyModel(
            id=data["id"],
            session_id=data["session_id"],
            data_type=data.get("data_type", ""),
            user_id=data["user_id"],
        )


# --- FakeContainer to simulate Cosmos DB behavior ---
class FakeContainer:
    def __init__(self, items=None):
        self.items = items if items is not None else []

    async def create_item(self, body):
        self.items.append(body)
        return body

    async def upsert_item(self, body):
        self.items = [item for item in self.items if item.get("id") != body.get("id")]
        self.items.append(body)
        return body

    async def read_item(self, item, partition_key):
        for doc in self.items:
            if doc.get("id") == item and doc.get("session_id") == partition_key:
                return doc
        raise Exception("Item not found")

    def query_items(self, query, parameters, **kwargs):
        async def gen():
            for item in self.items:
                yield item
        return gen()

    async def delete_item(self, item, partition_key):
        self.items = [doc for doc in self.items if doc.get("id") != item]
        return


# --- Fixture: cosmos_context ---
# We define this as a normal (synchronous) fixture so that it returns an actual instance.
@pytest.fixture
def cosmos_context(monkeypatch):
    # Patch asyncio.create_task to a no-op so that __init__ does not schedule initialize().
    monkeypatch.setattr(asyncio, "create_task", lambda coro, **kwargs: None)
    ctx = CosmosBufferedChatCompletionContext("test_session", "test_user", buffer_size=10)
    fake_container = FakeContainer()
    ctx._container = fake_container
    # Manually set the initialization event.
    ctx._initialized.set()
    return ctx


# Mark all tests in this module as async tests.
pytestmark = pytest.mark.asyncio


async def test_initialize(monkeypatch):
    """Test that initialize() creates the container and sets the event."""
    fake_container = FakeContainer()

    async def fake_create_container_if_not_exists(id, partition_key):
        return fake_container
    monkeypatch.setattr(
        "src.backend.context.cosmos_memory.Config.GetCosmosDatabaseClient",
        lambda: type("FakeDB", (), {"create_container_if_not_exists": fake_create_container_if_not_exists})
    )
    monkeypatch.setattr("src.backend.context.cosmos_memory.Config.COSMOSDB_CONTAINER", "mock-container")
    # For this test, let asyncio.create_task schedule normally.
    monkeypatch.setattr(asyncio, "create_task", lambda coro, **kwargs: asyncio.get_running_loop().create_task(coro))
    ctx = CosmosBufferedChatCompletionContext("s", "u", buffer_size=10)
    await ctx.initialize()
    assert ctx._container is fake_container


async def test_add_item_success(cosmos_context):
    dummy = DummyModel(id="dummy1", session_id="test_session", data_type="plan", user_id="test_user")
    await cosmos_context.add_item(dummy)
    assert any(item["id"] == "dummy1" for item in cosmos_context._container.items)


async def test_add_item_failure(cosmos_context, monkeypatch):
    dummy = DummyModel(id="dummy2", session_id="test_session", data_type="plan", user_id="test_user")

    async def fake_create_item(body):
        raise Exception("failure")
    monkeypatch.setattr(cosmos_context._container, "create_item", fake_create_item)
    # Exception is caught internally; no exception propagates.
    await cosmos_context.add_item(dummy)


async def test_update_item_success(cosmos_context):
    dummy = DummyModel(id="dummy3", session_id="test_session", data_type="plan", user_id="test_user")
    await cosmos_context.update_item(dummy)
    assert any(item["id"] == "dummy3" for item in cosmos_context._container.items)


async def test_update_item_failure(cosmos_context, monkeypatch):
    dummy = DummyModel(id="dummy4", session_id="test_session", data_type="plan", user_id="test_user")

    async def fake_upsert_item(body):
        raise Exception("failure")
    monkeypatch.setattr(cosmos_context._container, "upsert_item", fake_upsert_item)
    await cosmos_context.update_item(dummy)


async def test_get_item_by_id_success(cosmos_context):
    doc = {"id": "exists", "session_id": "test_partition", "data_type": "plan", "user_id": "test"}
    cosmos_context._container.items.append(doc)
    item = await cosmos_context.get_item_by_id("exists", "test_partition", DummyModel)
    assert item is not None
    assert item.id == "exists"


async def test_get_item_by_id_failure(cosmos_context):
    item = await cosmos_context.get_item_by_id("nonexistent", "test_partition", DummyModel)
    assert item is None


async def test_query_items_failure(cosmos_context, monkeypatch):
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: (_ for _ in ()).throw(Exception("fail")))
    result = await cosmos_context.query_items("dummy", [{"name": "param", "value": "val"}], DummyModel)
    assert result == []


async def test_add_session(cosmos_context):
    session = DummyModel(id="sess1", session_id="test_session", data_type="session", user_id="test_user")
    await cosmos_context.add_session(session)
    assert any(item["id"] == "sess1" for item in cosmos_context._container.items)


async def test_get_session_not_found(cosmos_context, monkeypatch):
    async def empty_gen():
        if False:
            yield {}
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: empty_gen())
    session = await cosmos_context.get_session("nonexistent")
    assert session is None


async def test_add_plan(cosmos_context):
    plan = DummyModel(id="plan1", session_id="test_session", data_type="plan", user_id="test_user")
    await cosmos_context.add_plan(plan)
    assert any(item["id"] == "plan1" for item in cosmos_context._container.items)


async def test_update_plan(cosmos_context):
    plan = DummyModel(id="plan1", session_id="test_session", data_type="plan", user_id="test_user")
    await cosmos_context.update_plan(plan)
    assert any(item["id"] == "plan1" for item in cosmos_context._container.items)


async def test_add_step(cosmos_context):
    step = DummyModel(id="step1", session_id="test_session", data_type="step", user_id="test_user")
    await cosmos_context.add_step(step)
    assert any(item["id"] == "step1" for item in cosmos_context._container.items)


async def test_update_step(cosmos_context):
    step = DummyModel(id="step1", session_id="test_session", data_type="step", user_id="test_user")
    await cosmos_context.update_step(step)
    assert any(item["id"] == "step1" for item in cosmos_context._container.items)


# --- Tests for Messages Methods ---
class DummyLLMMessage:
    def dict(self):
        return {"type": "UserMessage", "content": "hello"}


async def test_get_messages_failure(cosmos_context, monkeypatch):
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: (_ for _ in ()).throw(Exception("fail")))
    messages = await cosmos_context.get_messages()
    assert messages == []


async def test_get_data_by_type_failure(cosmos_context, monkeypatch):
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: (_ for _ in ()).throw(Exception("fail")))
    data = await cosmos_context.get_data_by_type("plan")
    assert data == []


# --- Utility Methods Tests ---
async def test_delete_item(cosmos_context):
    cosmos_context._container.items.append({"id": "del1", "session_id": "test_session"})
    await cosmos_context.delete_item("del1", "test_session")
    assert not any(item["id"] == "del1" for item in cosmos_context._container.items)


async def test_delete_items_by_query(cosmos_context, monkeypatch):
    async def gen():
        yield {"id": "del1", "session_id": "test_session"}
        yield {"id": "del2", "session_id": "test_session"}
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: gen())
    calls = []

    async def fake_delete_item(item, partition_key):
        calls.append((item, partition_key))
    monkeypatch.setattr(cosmos_context._container, "delete_item", fake_delete_item)
    await cosmos_context.delete_items_by_query("query", [{"name": "param", "value": "val"}])
    assert len(calls) == 2


async def test_delete_all_messages(cosmos_context, monkeypatch):
    async def gen():
        yield {"id": "msg1", "session_id": "test_session"}
        yield {"id": "msg2", "session_id": "test_session"}
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: gen())
    calls = []

    async def fake_delete_item(item, partition_key):
        calls.append((item, partition_key))
    monkeypatch.setattr(cosmos_context._container, "delete_item", fake_delete_item)
    await cosmos_context.delete_all_messages("message")
    assert len(calls) == 2


async def test_get_all_messages_failure(cosmos_context, monkeypatch):
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: (_ for _ in ()).throw(Exception("fail")))
    messages = await cosmos_context.get_all_messages()
    assert messages == []


async def test_close(cosmos_context):
    await cosmos_context.close()


async def test_context_manager(cosmos_context):
    async with cosmos_context as ctx:
        assert ctx == cosmos_context


async def test_get_all_sessions_failure(cosmos_context, monkeypatch):
    """Simulate an exception during query_items in get_all_sessions, which should return an empty list."""
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: (_ for _ in ()).throw(Exception("fail")))
    sessions = await cosmos_context.get_all_sessions()
    assert sessions == []


async def test_get_plan_by_session_not_found(cosmos_context, monkeypatch):
    """Simulate query_items returning no plans, so get_plan_by_session returns None."""
    async def empty_gen():
        if False:
            yield {}
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: empty_gen())
    plan = await cosmos_context.get_plan_by_session("nonexistent")
    assert plan is None


async def test_get_all_plans_failure(cosmos_context, monkeypatch):
    """Simulate exception in query_items when calling get_all_plans; should return empty list."""
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: (_ for _ in ()).throw(Exception("fail")))
    plans = await cosmos_context.get_all_plans()
    assert plans == []


async def test_get_messages_unrecognized(cosmos_context, monkeypatch):
    """Test get_messages() when an item has an unrecognized message type so it is skipped."""
    async def gen():
        yield {"id": "msg_unknown", "session_id": "test_session", "data_type": "message",
               "content": {"type": "UnknownType", "content": "ignored"}, "_ts": 50}
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: gen())
    messages = await cosmos_context.get_messages()
    # Since the type is unknown, the message should be skipped.
    assert messages == []


async def test_delete_item_failure(cosmos_context, monkeypatch):
    """Simulate an exception in delete_item so that delete_item() logs and does not propagate."""
    async def fake_delete_item(item, partition_key):
        raise Exception("delete failure")
    monkeypatch.setattr(cosmos_context._container, "delete_item", fake_delete_item)
    # Calling delete_item should not raise; it catches exception internally.
    await cosmos_context.delete_item("any", "any")


async def test_delete_items_by_query_failure(cosmos_context, monkeypatch):
    """Simulate an exception in query_items within delete_items_by_query and ensure it is caught."""
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: (_ for _ in ()).throw(Exception("fail")))
    # delete_items_by_query should catch the exception and not propagate.
    await cosmos_context.delete_items_by_query("query", [{"name": "param", "value": "val"}])


async def test_get_all_messages_success(cosmos_context, monkeypatch):
    async def gen():
        yield {"id": "msg1", "session_id": "test_session", "data_type": "message", "content": "hello", "_ts": 40}
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: gen())
    messages = await cosmos_context.get_all_messages()
    assert len(messages) == 1
    assert messages[0]["id"] == "msg1"


async def test_get_all_messages_exception(cosmos_context, monkeypatch):
    monkeypatch.setattr(cosmos_context._container, "query_items",
                        lambda query, parameters, **kwargs: (_ for _ in ()).throw(Exception("fail")))
    messages = await cosmos_context.get_all_messages()
    assert messages == []

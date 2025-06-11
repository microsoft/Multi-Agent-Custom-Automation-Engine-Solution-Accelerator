# src/tests/backend/context/test_cosmos_memory.py
import sys
import types
import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from types import SimpleNamespace
from semantic_kernel.contents import ChatHistory
from semantic_kernel.memory.memory_record import MemoryRecord

# -----------------------------------------------
# Mock models.messages_kernel and MemoryRecord
# -----------------------------------------------
mock_messages_module = types.ModuleType("models.messages_kernel")

class BaseDataModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def model_dump(self):
        return self.__dict__

    @classmethod
    def model_validate(cls, data):
        return cls(**data)


class Session(BaseDataModel):
    def __init__(self, id, session_id, user_id, data_type, **kwargs):
        self.id = id
        self.session_id = session_id
        self.user_id = user_id
        self.data_type = data_type

class Plan(Session): pass
class Step(Session): pass
class AgentMessage(Session): pass

# ✅ Correctly mocked MemoryRecord with 'is_reference'
class MemoryRecord:
    def __init__(self, id, text, description, external_source_name,
                 additional_metadata, embedding, key, is_reference):
        self.id = id
        self.text = text
        self.description = description
        self.external_source_name = external_source_name
        self.additional_metadata = additional_metadata
        self.embedding = None if embedding is None else np.array(embedding)
        self.key = key
        self.is_reference = is_reference


# Register all mocks
mock_messages_module.BaseDataModel = BaseDataModel
mock_messages_module.Session = Session
mock_messages_module.Plan = Plan
mock_messages_module.Step = Step
mock_messages_module.AgentMessage = AgentMessage
mock_messages_module.MemoryRecord = MemoryRecord

# ✅ Inject into sys.modules BEFORE importing the target
sys.modules["models.messages_kernel"] = mock_messages_module
sys.modules["semantic_kernel.memory.memory_record"] = mock_messages_module

# -----------------------------------------------
# Mock app_config
# -----------------------------------------------
mock_app_config = types.ModuleType("app_config")
mock_app_config.config = MagicMock()
mock_app_config.config.COSMOSDB_ENDPOINT = "https://dummy-endpoint"
mock_app_config.config.COSMOSDB_DATABASE = "dummy-db"
mock_app_config.config.COSMOSDB_CONTAINER = "dummy-container"
sys.modules["app_config"] = mock_app_config

# ✅ NOW import the class under test
from src.backend.context.cosmos_memory_kernel import CosmosMemoryContext


# -----------------------------------------------
# Utility: async iterator mock
# -----------------------------------------------
class AsyncIterator:
    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)

# -----------------------------------------------
# Fixture for test context
# -----------------------------------------------
@pytest.fixture
def memory_context():
    context = CosmosMemoryContext(session_id="test-session", user_id="test-user")
    context._container = AsyncMock()
    context._container.query_items = MagicMock()
    context._initialized.set()
    return context

# -----------------------------------------------
# Tests
# -----------------------------------------------
@pytest.mark.asyncio
async def test_add_item(memory_context):
    dummy = Session(id="1", session_id="test-session", user_id="test-user", data_type="session")
    await memory_context.add_item(dummy)
    memory_context._container.create_item.assert_called_once()

@pytest.mark.asyncio
async def test_update_item(memory_context):
    dummy = Plan(id="1", session_id="test-session", user_id="test-user", data_type="plan")
    await memory_context.update_item(dummy)
    memory_context._container.upsert_item.assert_called_once()

@pytest.mark.asyncio
async def test_get_item_by_id(memory_context):
    item_data = {"id": "1", "session_id": "test-session", "user_id": "test-user", "data_type": "session"}
    memory_context._container.read_item = AsyncMock(return_value=item_data)
    item = await memory_context.get_item_by_id("1", "test-session", Session)
    assert isinstance(item, Session)
    assert item.id == "1"

@pytest.mark.asyncio
async def test_query_items(memory_context):
    mock_items = [{"id": "1", "session_id": "test-session", "user_id": "test-user", "data_type": "step", "_ts": 123}]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_items.copy()))
    results = await memory_context.query_items("SELECT * FROM c", [], Step)
    assert len(results) == 1
    assert isinstance(results[0], Step)

@pytest.mark.asyncio
async def test_add_message(memory_context):
    msg = ChatMessageContent(
        role=AuthorRole.USER,
        content="Hello",
        metadata={"source": "test"}
    )
    await memory_context.add_message(msg)
    memory_context._container.create_item.assert_called_once()

@pytest.mark.asyncio
async def test_get_messages(memory_context):
    message_data = {
        "id": "1",
        "session_id": "test-session",
        "user_id": "test-user",
        "data_type": "message",
        "content": {
            "role": "user",
            "content": "Hi",
            "metadata": {}
        },
        "_ts": 123
    }
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([message_data]))
    messages = await memory_context.get_messages()
    assert len(messages) == 1
    assert messages[0].content == "Hi"



@pytest.mark.asyncio
async def test_initialize_logs_error_on_failure(monkeypatch, caplog):
    monkeypatch.setattr("src.backend.context.cosmos_memory_kernel.CosmosClient", MagicMock(side_effect=Exception("fail")))
    context = CosmosMemoryContext("session", "user")
    context._initialized.clear()
    await context.initialize()
    assert "Failed to initialize CosmosDB container" in caplog.text

@pytest.mark.asyncio
async def test_add_session(memory_context):
    session = Session(id="s1", session_id="test-session", user_id="test-user", data_type="session")
    await memory_context.add_session(session)
    memory_context._container.create_item.assert_called_once()


@pytest.mark.asyncio
async def test_add_and_update_plan(memory_context):
    plan = Plan(id="p1", session_id="test-session", user_id="test-user", data_type="plan")
    await memory_context.add_plan(plan)
    await memory_context.update_plan(plan)
    assert memory_context._container.create_item.called
    assert memory_context._container.upsert_item.called



@pytest.mark.asyncio
async def test_upsert_memory_record(memory_context):
    record = MagicMock()
    record.id = "mid"
    record.text = "t"
    record.key = "k"
    record.description = "d"
    record.external_source_name = "e"
    record.additional_metadata = "m"
    record.embedding = None
    await memory_context.upsert_memory_record("test", record)
    memory_context._container.upsert_item.assert_called_once()


@pytest.mark.asyncio
async def test_delete_item(memory_context):
    await memory_context.delete_item("id", "partition")
    memory_context._container.delete_item.assert_called_once()


@pytest.mark.asyncio
async def test_remove_memory_record(memory_context):
    mock_data = [{"id": "1"}]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_data))
    await memory_context.remove_memory_record("coll", "key")
    memory_context._container.delete_item.assert_called_once()



def test_get_chat_history():
    msg = ChatMessageContent(role=AuthorRole.USER, content="hi", metadata={})
    context = CosmosMemoryContext("session", "user", initial_messages=[msg])
    history = context.get_chat_history()
    assert history.messages[0].content == "hi"

class AsyncIterator:
    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


@pytest.mark.asyncio
async def test_initialize_sets_container_on_success(monkeypatch):
    mock_db = AsyncMock()
    mock_container = AsyncMock()
    mock_db.create_container_if_not_exists = AsyncMock(return_value=mock_container)
    mock_client = AsyncMock()
    mock_client.get_database_client = MagicMock(return_value=mock_db)

    monkeypatch.setattr("src.backend.context.cosmos_memory_kernel.CosmosClient", MagicMock(return_value=mock_client))
    monkeypatch.setattr("src.backend.context.cosmos_memory_kernel.DefaultAzureCredential", MagicMock())

    context = CosmosMemoryContext("session", "user")
    context._initialized.clear()
    await context.initialize()
    assert context._container == mock_container

@pytest.mark.asyncio
async def test_get_session_found(memory_context):
    mock_data = {
        "id": "s1",
        "session_id": "test-session",
        "user_id": "test-user",
        "data_type": "session",
        "_ts": 123456
    }
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([mock_data]))
    session = await memory_context.get_session("s1")
    assert session.id == "s1"

@pytest.mark.asyncio
async def test_get_memory_record_found(memory_context, monkeypatch):
    # ✅ Patch MemoryRecord used in cosmos_memory_kernel
    from types import SimpleNamespace

    def mock_memory_record(id, text, description, external_source_name,
                       additional_metadata, embedding, key, is_reference=False):
        return SimpleNamespace(
            id=id,
            text=text,
            description=description,
            external_source_name=external_source_name,
            additional_metadata=additional_metadata,
            embedding=np.array(embedding),
            key=key,
            is_reference=is_reference,
        )

    monkeypatch.setattr("src.backend.context.cosmos_memory_kernel.MemoryRecord", mock_memory_record)


    mock_record = {
        "id": "m1",
        "text": "test",
        "description": "desc",
        "external_source_name": "ext",
        "additional_metadata": "meta",
        "key": "key",
        "embedding": [0.1, 0.2],
        "is_reference": False
    }

    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([mock_record]))
    record = await memory_context.get_memory_record("test-collection", "key", with_embedding=True)
    assert record.id == "m1"
    assert isinstance(record.embedding, np.ndarray)



@pytest.mark.asyncio
async def test_get_all_sessions(memory_context):
    mock_data = [{
        "id": "1",
        "session_id": "test-session",
        "user_id": "test-user",
        "data_type": "session",
        "_ts": 123456
    }]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_data))
    sessions = await memory_context.get_all_sessions()
    assert isinstance(sessions[0], Session)

@pytest.mark.asyncio
async def test_get_nearest_matches(memory_context):
    fake_embedding = np.array([0.1, 0.2])
    record_mock = MagicMock(spec=MemoryRecord)
    record_mock.id = "m1"
    record_mock.key = "key"
    record_mock.text = "sample"
    record_mock.description = "desc"
    record_mock.external_source_name = "ext"
    record_mock.additional_metadata = "meta"
    record_mock.embedding = np.array([0.1, 0.2])
    record_mock.is_reference = False

    memory_context.get_memory_records = AsyncMock(return_value=[record_mock])
    matches = await memory_context.get_nearest_matches("test", fake_embedding, 1)
    assert isinstance(matches, list)
    assert len(matches) == 1
    assert isinstance(matches[0][0], MemoryRecord) or hasattr(matches[0][0], "embedding")

@pytest.mark.asyncio
async def test_get_memory_record_found_without_embedding(memory_context, monkeypatch):
    def mock_memory_record(id, text, description, external_source_name,
                           additional_metadata, embedding, key, is_reference=False):
        return SimpleNamespace(
            id=id,
            text=text,
            description=description,
            external_source_name=external_source_name,
            additional_metadata=additional_metadata,
            embedding=embedding,
            key=key,
            is_reference=is_reference,
        )

    monkeypatch.setattr("src.backend.context.cosmos_memory_kernel.MemoryRecord", mock_memory_record)

    mock_record = {
        "id": "m1",
        "text": "test",
        "description": "desc",
        "external_source_name": "ext",
        "additional_metadata": "meta",
        "key": "key",
        # 'embedding' omitted to simulate missing vector
        "is_reference": False
    }

    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([mock_record]))
    record = await memory_context.get_memory_record("test-collection", "key", with_embedding=False)
    assert record.embedding is None

@pytest.mark.asyncio
async def test_get_memory_records_with_and_without_embeddings(memory_context, monkeypatch):
    def mock_memory_record(id, text, description, external_source_name,
                       additional_metadata, embedding, key, is_reference=False):
        return SimpleNamespace(
            id=id,
            text=text,
            description=description,
            external_source_name=external_source_name,
            additional_metadata=additional_metadata,
            embedding=np.array(embedding) if embedding is not None else None,
            key=key,
            is_reference=is_reference,
        )

    monkeypatch.setattr("src.backend.context.cosmos_memory_kernel.MemoryRecord", mock_memory_record)

    mock_items = [
        {
            "id": "m1",
            "text": "test",
            "description": "desc",
            "external_source_name": "ext",
            "additional_metadata": "meta",
            "embedding": [0.1, 0.2],
            "key": "k1",
        }
    ]

    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_items.copy()))
    records = await memory_context.get_memory_records("collection", with_embeddings=True)
    assert isinstance(records[0], SimpleNamespace)
    assert isinstance(records[0].embedding, np.ndarray)

    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_items.copy()))
    records = await memory_context.get_memory_records("collection", with_embeddings=False)
    assert records[0].embedding is None

@pytest.mark.asyncio
async def test_upsert_memory_record(memory_context):
    record = MagicMock()
    record.id = "rec-id"
    record.text = "text"
    record.description = "desc"
    record.external_source_name = "ext"
    record.additional_metadata = "meta"
    record.embedding = np.array([0.1, 0.2])
    record.key = "my-key"

    result = await memory_context.upsert_memory_record("my-collection", record)
    assert result == "rec-id"
    memory_context._container.upsert_item.assert_called_once()

@pytest.mark.asyncio
async def test_remove_memory_record(memory_context):
    mock_item = {"id": "doc1"}
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([mock_item]))
    await memory_context.remove_memory_record("collection", "key")
    memory_context._container.delete_item.assert_called_once_with(item="doc1", partition_key="test-session")

@pytest.mark.asyncio
async def test_get_all_messages(memory_context):
    mock_messages = [{"id": "1", "user_id": "test-user"}]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_messages.copy()))
    results = await memory_context.get_all_messages()
    assert isinstance(results, list)
    assert results[0]["id"] == "1"

@pytest.mark.asyncio
async def test_get_all_items(memory_context):
    memory_context.get_all_messages = AsyncMock(return_value=[{"id": "1"}])
    results = await memory_context.get_all_items()
    assert isinstance(results, list)
    assert results[0]["id"] == "1"
@pytest.mark.asyncio
async def test_delete_items_by_query(memory_context):
    mock_items = [{"id": "1", "session_id": "test-session"}]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_items.copy()))
    await memory_context.delete_items_by_query("fake-query", [])
    memory_context._container.delete_item.assert_called_once_with(item="1", partition_key="test-session")

@pytest.mark.asyncio
async def test_delete_all_messages(memory_context):
    memory_context.delete_items_by_query = AsyncMock()
    await memory_context.delete_all_messages("memory")
    memory_context.delete_items_by_query.assert_called_once()

@pytest.mark.asyncio
async def test_delete_all_items(memory_context):
    memory_context.delete_all_messages = AsyncMock()
    await memory_context.delete_all_items("memory")
    memory_context.delete_all_messages.assert_called_once()

@pytest.mark.asyncio
async def test_does_collection_exist_true(memory_context):
    memory_context.get_collections = AsyncMock(return_value=["existing"])
    assert await memory_context.does_collection_exist("existing") is True

@pytest.mark.asyncio
async def test_does_collection_exist_false(memory_context):
    memory_context.get_collections = AsyncMock(return_value=["other"])
    assert await memory_context.does_collection_exist("missing") is False

@pytest.mark.asyncio
async def test_get_collections(memory_context):
    mock_items = [{"collection": "test-collection"}]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_items.copy()))
    result = await memory_context.get_collections()
    assert result == ["test-collection"]

@pytest.mark.asyncio
async def test_delete_collection(memory_context):
    mock_items = [{"id": "1", "session_id": "test-session"}]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_items.copy()))
    await memory_context.delete_collection("my-collection")
    memory_context._container.delete_item.assert_called_once_with(item="1", partition_key="test-session")

@pytest.mark.asyncio
async def test_get_collections_empty(memory_context):
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([]))
    collections = await memory_context.get_collections()
    assert collections == []

@pytest.mark.asyncio
async def test_delete_collection_no_items(memory_context):
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([]))
    await memory_context.delete_collection("empty-collection")
    memory_context._container.delete_item.assert_not_called()

@pytest.mark.asyncio
async def test_get_all_messages_error_fallback(memory_context):
    def failing_query(*args, **kwargs):
        raise Exception("fail")

    memory_context._container.query_items = failing_query
    results = await memory_context.get_all_messages()
    assert results == []

@pytest.mark.asyncio
async def test_delete_items_by_query_error(memory_context):
    def broken_query(*args, **kwargs):
        raise Exception("boom")

    memory_context._container.query_items = broken_query
    await memory_context.delete_items_by_query("SELECT * FROM c", [])  # should not raise

@pytest.mark.asyncio
async def test_get_memory_records_exception(memory_context):
    def broken_query(*args, **kwargs):
        raise Exception("fail")

    memory_context._container.query_items = broken_query
    records = await memory_context.get_memory_records("some-collection")
    assert records == []

@pytest.mark.asyncio
async def test_get_nearest_matches_with_min_score(memory_context):
    target = np.array([1.0, 0.0])
    close = MagicMock()
    close.embedding = np.array([0.7, 0.7])  # gives sim ≈ 0.707
    close.id = "low-sim"
    memory_context.get_memory_records = AsyncMock(return_value=[close])

    matches = await memory_context.get_nearest_matches("coll", target, limit=1, min_relevance_score=0.99)
    assert matches == []  # filtered out

@pytest.mark.asyncio
async def test_save_chat_history(memory_context):
    msg = ChatMessageContent(role=AuthorRole.USER, content="hello", metadata={})
    history = ChatHistory()
    history.add_message(msg)

    memory_context.add_message = AsyncMock()
    await memory_context.save_chat_history(history)
    memory_context.add_message.assert_called_once_with(msg)

@pytest.mark.asyncio
async def test_get_nearest_match(memory_context):
    record = MagicMock()
    record.embedding = np.array([1.0, 0.0])
    memory_context.get_memory_records = AsyncMock(return_value=[record])

    result, score = await memory_context.get_nearest_match("coll", np.array([1.0, 0.0]))
    assert result is not None
    assert score == 1.0


@pytest.mark.asyncio
async def test_delete_items_by_query_error(memory_context):
    memory_context._container.query_items = MagicMock(side_effect=Exception("fail"))
    await memory_context.delete_items_by_query("SELECT * FROM c", [])  # Should not raise

@pytest.mark.asyncio
async def test_get_collections_empty_result(memory_context):
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([]))
    collections = await memory_context.get_collections()
    assert collections == []

@pytest.mark.asyncio
async def test_delete_collection_nothing_to_delete(memory_context):
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([]))
    await memory_context.delete_collection("non-existent")
    memory_context._container.delete_item.assert_not_called()

@pytest.mark.asyncio
async def test_get_memory_record_not_found(memory_context):
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([]))
    record = await memory_context.get_memory_record("collection", "missing-key")
    assert record is None

@pytest.mark.asyncio
async def test_get_step(memory_context):
    step_data = {"id": "step1", "session_id": "test-session", "user_id": "test-user", "data_type": "step"}
    memory_context._container.read_item = AsyncMock(return_value=step_data)
    step = await memory_context.get_step("step1", "test-session")
    assert isinstance(step, Step)

@pytest.mark.asyncio
async def test_get_steps_for_plan(memory_context):
    memory_context.get_steps_by_plan = AsyncMock(return_value=[Step(id="s", session_id="test-session", user_id="test-user", data_type="step")])
    steps = await memory_context.get_steps_for_plan("plan-id")
    assert len(steps) == 1

@pytest.mark.asyncio
async def test_get_data_by_type_default_model(memory_context):
    mock_item = {"id": "x", "session_id": "test-session", "user_id": "test-user", "data_type": "custom","_ts": 1234567890 }
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([mock_item]))
    result = await memory_context.get_data_by_type("custom")
    assert isinstance(result[0], BaseDataModel)

@pytest.mark.asyncio
async def test_upsert_async_adds_id_and_session(memory_context):
    record = {"text": "test"}
    result_id = await memory_context.upsert_async("test-collection", record)
    assert result_id != ""
    memory_context._container.upsert_item.assert_called_once()

@pytest.mark.asyncio
async def test_remove_batch(memory_context):
    memory_context.remove_memory_record = AsyncMock()
    await memory_context.remove_batch("collection", ["k1", "k2"])
    assert memory_context.remove_memory_record.call_count == 2

def test_del_logs_warning(monkeypatch):
    context = CosmosMemoryContext("session", "user")

    def raise_in_close():
        raise Exception("fail")

    monkeypatch.setattr(context, "close", raise_in_close)

    try:
        del context  # Should not raise
    except Exception:
        pytest.fail("Exception should not be raised in __del__")

@pytest.mark.asyncio
async def test_get_step_not_found(memory_context):
    memory_context._container.read_item = AsyncMock(side_effect=Exception("not found"))
    step = await memory_context.get_step("step-id", "partition-key")
    assert step is None



@pytest.mark.asyncio
async def test_get_steps_by_plan(memory_context):
    step_data = {
        "id": "step1",
        "session_id": "test-session",
        "user_id": "test-user",
        "data_type": "step",
        "_ts": 123
    }
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([step_data]))
    result = await memory_context.get_steps_by_plan("plan1")
    assert isinstance(result[0], Step)

@pytest.mark.asyncio
async def test_save_chat_history_empty(memory_context):
    from semantic_kernel.contents import ChatHistory
    empty_history = ChatHistory()
    await memory_context.save_chat_history(empty_history)
    # Should do nothing; no error

@pytest.mark.asyncio
async def test_delete_items_by_query_failure(memory_context):
    memory_context._container.query_items = MagicMock(side_effect=Exception("fail"))
    await memory_context.delete_items_by_query("fake-query", [])  # should not raise

@pytest.mark.asyncio
async def test_get_collections_empty(memory_context):
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([]))
    result = await memory_context.get_collections()
    assert result == []

def test_del_exception_logs(monkeypatch):
    context = CosmosMemoryContext("session", "user")

    def raise_on_close():
        raise Exception("forced")

    monkeypatch.setattr(context, "close", raise_on_close)
    try:
        del context
    except Exception:
        pytest.fail("Exception should not be raised in __del__")

@pytest.mark.asyncio
async def test_initialize_logs_error_on_container_failure(monkeypatch, caplog):
    from src.backend.context.cosmos_memory_kernel import CosmosMemoryContext

    context = CosmosMemoryContext("session", "user")
    context._initialized.clear()

    mock_client = AsyncMock()
    mock_db = AsyncMock()
    mock_db.create_container_if_not_exists = AsyncMock(side_effect=Exception("boom"))
    mock_client.get_database_client.return_value = mock_db

    monkeypatch.setattr("src.backend.context.cosmos_memory_kernel.CosmosClient", lambda *_: mock_client)
    monkeypatch.setattr("src.backend.context.cosmos_memory_kernel.DefaultAzureCredential", lambda: None)

    await context.initialize()

    assert "Failed to initialize CosmosDB container" in caplog.text



@pytest.mark.asyncio
async def test_get_item_by_id_failure(memory_context):
    memory_context._container.read_item = AsyncMock(side_effect=Exception("not found"))
    result = await memory_context.get_item_by_id("x", "partition", BaseDataModel)
    assert result is None

@pytest.mark.asyncio
async def test_get_steps_by_plan_normal(memory_context):
    item = {
        "id": "s1", "session_id": "test-session", "user_id": "test-user",
        "data_type": "step", "_ts": 123
    }
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([item]))
    steps = await memory_context.get_steps_by_plan("p1")
    assert isinstance(steps[0], Step)




@pytest.mark.asyncio
async def test_get_item_by_id_exception_returns_none(memory_context):
    memory_context._container.read_item = AsyncMock(side_effect=Exception("fail"))
    result = await memory_context.get_item_by_id("id", "partition", BaseDataModel)
    assert result is None

@pytest.mark.asyncio
async def test_get_steps_by_plan_normal(memory_context):
    item = {
        "id": "s1", "session_id": "test-session", "user_id": "test-user",
        "data_type": "step", "_ts": 123
    }
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([item]))
    steps = await memory_context.get_steps_by_plan("p1")
    assert isinstance(steps[0], Step)

@pytest.mark.asyncio
async def test_save_chat_history_no_messages(memory_context):
    from semantic_kernel.contents import ChatHistory
    history = ChatHistory()
    await memory_context.save_chat_history(history)  # no exception

@pytest.mark.asyncio
async def test_get_collections_empty_result(memory_context):
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([]))
    collections = await memory_context.get_collections()
    assert collections == []

@pytest.mark.asyncio
async def test_delete_collection_none_found(memory_context):
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator([]))
    await memory_context.delete_collection("test")
    memory_context._container.delete_item.assert_not_called()

@pytest.mark.asyncio
async def test_delete_items_by_query_handles_error(memory_context):
    memory_context._container.query_items = MagicMock(side_effect=Exception("DB failure"))
    await memory_context.delete_items_by_query("SELECT * FROM c", [])

def test_del_exception_is_handled(monkeypatch):
    context = CosmosMemoryContext("session", "user")
    monkeypatch.setattr(context, "close", lambda: (_ for _ in ()).throw(Exception("fail")))
    try:
        del context
    except Exception:
        pytest.fail("Exception in __del__ should be suppressed")

@pytest.mark.asyncio
async def test_get_thread_by_session(memory_context):
    mock_data = [{
        "id": "t1",
        "session_id": "test-session",
        "user_id": "test-user",
        "data_type": "thread",
        "_ts": 123456
    }]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_data.copy()))
    thread = await memory_context.get_thread_by_session("test-session")
    assert thread.id == "t1"

@pytest.mark.asyncio
async def test_get_plan_by_session(memory_context):
    mock_data = [{
        "id": "p1",
        "session_id": "test-session",
        "user_id": "test-user",
        "data_type": "plan",
        "_ts": 123456
    }]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_data.copy()))
    plan = await memory_context.get_plan_by_session("test-session")
    assert plan.id == "p1"

@pytest.mark.asyncio
async def test_get_all_plans(memory_context):
    mock_data = [{
        "id": "p1",
        "session_id": "test-session",
        "user_id": "test-user",
        "data_type": "plan",
        "_ts": 123456
    }]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_data.copy()))
    plans = await memory_context.get_all_plans()
    assert len(plans) == 1


@pytest.mark.asyncio
async def test_add_agent_message(memory_context):
    agent_msg = AgentMessage(id="m1", session_id="test-session", user_id="test-user", data_type="agent_message")
    await memory_context.add_agent_message(agent_msg)
    memory_context._container.create_item.assert_called_once()

@pytest.mark.asyncio
async def test_get_agent_messages_by_session(memory_context):
    mock_data = [{
        "id": "m1",
        "session_id": "test-session",
        "user_id": "test-user",
        "data_type": "agent_message",
        "_ts": 123456
    }]
    memory_context._container.query_items = MagicMock(return_value=AsyncIterator(mock_data.copy()))
    messages = await memory_context.get_agent_messages_by_session("test-session")
    assert messages[0].id == "m1"

@pytest.mark.asyncio
async def test_upsert_batch(memory_context):
    record = MemoryRecord(
        id="id1",
        text="text",
        description="desc",
        external_source_name="ext",
        additional_metadata="meta",
        embedding=np.array([0.1, 0.2]),
        key="k",
        is_reference=False
    )
    memory_context.upsert_memory_record = AsyncMock(return_value="id1")
    ids = await memory_context.upsert_batch("collection", [record])
    assert ids == ["id1"]

@pytest.mark.asyncio
async def test_get_batch(memory_context):
    record = MemoryRecord(
        id="id1",
        text="text",
        description="desc",
        external_source_name="ext",
        additional_metadata="meta",
        embedding=np.array([0.1, 0.2]),
        key="k",
        is_reference=False
    )
    memory_context.get_memory_record = AsyncMock(return_value=record)
    records = await memory_context.get_batch("collection", ["k"], with_embeddings=True)
    assert len(records) == 1


@pytest.mark.asyncio
async def test_get_alias(memory_context):
    memory_context.get_memory_record = AsyncMock(return_value="record")
    result = await memory_context.get("collection", "key", with_embedding=True)
    assert result == "record"

@pytest.mark.asyncio
async def test_remove_alias(memory_context):
    memory_context.remove_memory_record = AsyncMock()
    await memory_context.remove("collection", "key")
    memory_context.remove_memory_record.assert_called_once()


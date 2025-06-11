# src/tests/backend/test_app_kernel_simple.py
import sys
import types
import importlib
import pytest
import asyncio

@pytest.fixture(autouse=True)
def stub_dependencies(monkeypatch):
    """
    Stub out all external dependencies of backend.app_kernel so that importing it
    (and calling a few of its functions) succeeds without raising ModuleNotFoundError.
    """
    # -------------------------------------------------------------------------
    # Stub app_config
    # -------------------------------------------------------------------------
    app_config_mod = types.ModuleType("app_config")
    class DummyConfig:
        FRONTEND_SITE_NAME = "http://localhost"
        AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4o"
        AZURE_OPENAI_API_VERSION = "2024-11-20"
        AZURE_OPENAI_ENDPOINT = "https://dummy"
        AZURE_OPENAI_SCOPES = ["https://dummy/.default"]
        AZURE_AI_SUBSCRIPTION_ID = "sub"
        AZURE_AI_RESOURCE_GROUP = "rg"
        AZURE_AI_PROJECT_NAME = "pn"
        AZURE_AI_AGENT_PROJECT_CONNECTION_STRING = "cs"
        COSMOSDB_ENDPOINT = "https://cosmos"
        COSMOSDB_DATABASE = "db"
        COSMOSDB_CONTAINER = "coll"
        FRONTEND_SITE_NAME = "http://localhost:3000"

        def _get_required(self, name, default=None):
            return getattr(self, name)

        def _get_optional(self, name, default=""):
            return default

        def _get_bool(self, name):
            return False

        def get_azure_credentials(self):
            return None

        def get_cosmos_database_client(self):
            return DummyCosmosDB("db_client:" + self.COSMOSDB_DATABASE)

        def create_kernel(self):
            return "kernel"

        def get_ai_project_client(self):
            return None

        async def create_azure_ai_agent(self, agent_name, instructions, tools=None, client=None, response_format=None, temperature=0.0):
            return DummyAzureAIAgent()

    app_config_mod.config = DummyConfig()
    sys.modules["app_config"] = app_config_mod

    # -------------------------------------------------------------------------
    # Stub auth.auth_utils.get_authenticated_user_details
    # -------------------------------------------------------------------------
    auth_pkg = types.ModuleType("auth")
    auth_utils_mod = types.ModuleType("auth.auth_utils")
    def fake_get_authenticated_user_details(request_headers):
        # By default, return a “valid” user_id
        return {"user_principal_id": "testuser"}
    auth_utils_mod.get_authenticated_user_details = fake_get_authenticated_user_details
    auth_pkg.auth_utils = auth_utils_mod
    sys.modules["auth"] = auth_pkg
    sys.modules["auth.auth_utils"] = auth_utils_mod

    # -------------------------------------------------------------------------
    # Stub config_kernel.Config
    # -------------------------------------------------------------------------
    config_kernel_mod = types.ModuleType("config_kernel")
    class DummyConfigKernel:
        FRONTEND_SITE_NAME = "http://localhost"
    config_kernel_mod.Config = DummyConfigKernel
    sys.modules["config_kernel"] = config_kernel_mod

    # -------------------------------------------------------------------------
    # Stub context.cosmos_memory_kernel.CosmosMemoryContext
    # -------------------------------------------------------------------------
    context_pkg = types.ModuleType("context")
    cosmos_mod = types.ModuleType("context.cosmos_memory_kernel")
    class DummyCosmosContext:
        def __init__(self, session_id=None, user_id=None):
            # pretend to store session_id/user_id
            self.session_id = session_id
            self.user_id = user_id

        # Minimal async stubs for plan/step/message retrieval/deletion:
        async def get_plan_by_session(self, session_id):
            # Return None or a dummy plan object
            return None

        async def get_steps_by_plan(self, plan_id):
            return []

        async def get_all_plans(self):
            return []

        async def get_steps_for_plan(self, plan_id):
            return []

        async def get_data_by_type(self, data_type):
            return []

        async def delete_all_items(self, data_type):
            return None

        async def get_all_items(self):
            return []
    cosmos_mod.CosmosMemoryContext = DummyCosmosContext
    context_pkg.cosmos_memory_kernel = cosmos_mod
    sys.modules["context"] = context_pkg
    sys.modules["context.cosmos_memory_kernel"] = cosmos_mod

    # -------------------------------------------------------------------------
    # Stub event_utils.track_event_if_configured
    # -------------------------------------------------------------------------
    event_utils_mod = types.ModuleType("event_utils")
    def fake_track_event_if_configured(name, data):
        # no-op
        return None
    event_utils_mod.track_event_if_configured = fake_track_event_if_configured
    sys.modules["event_utils"] = event_utils_mod

    # -------------------------------------------------------------------------
    # Stub semantic_kernel and its submodules
    # -------------------------------------------------------------------------
    sk_pkg = types.ModuleType("semantic_kernel")
    sk_pkg.__path__ = []
    sk_kernel_mod = types.ModuleType("semantic_kernel.kernel")
    sk_kernel_mod.Kernel = lambda : "kernel-object"
    sk_pkg.kernel = sk_kernel_mod
    sk_contents_mod = types.ModuleType("semantic_kernel.contents")
    sk_contents_mod.ChatHistory = lambda *args, **kwargs: None
    sk_pkg.contents = sk_contents_mod
    sk_funcs_pkg = types.ModuleType("semantic_kernel.functions")
    sk_funcs_pkg.KernelFunction = lambda *args, **kwargs: (lambda f: f)
    # Stub kernel_arguments
    kernel_args_mod = types.ModuleType("semantic_kernel.functions.kernel_arguments")
    kernel_args_mod.KernelArguments = type("KernelArguments", (), {})
    sk_funcs_pkg.kernel_arguments = kernel_args_mod
    sys.modules["semantic_kernel"] = sk_pkg
    sys.modules["semantic_kernel.kernel"] = sk_kernel_mod
    sys.modules["semantic_kernel.contents"] = sk_contents_mod
    sys.modules["semantic_kernel.functions"] = sk_funcs_pkg
    sys.modules["semantic_kernel.functions.kernel_arguments"] = kernel_args_mod

    # -------------------------------------------------------------------------
    # Stub Azure monitor
    # -------------------------------------------------------------------------
    azure_pkg = types.ModuleType("azure")
    monitor_pkg = types.ModuleType("azure.monitor")
    otel_pkg = types.ModuleType("azure.monitor.opentelemetry")
    otel_pkg.configure_azure_monitor = lambda **kwargs: None
    monitor_pkg.opentelemetry = otel_pkg
    azure_pkg.monitor = monitor_pkg
    sys.modules["azure"] = azure_pkg
    sys.modules["azure.monitor"] = monitor_pkg
    sys.modules["azure.monitor.opentelemetry"] = otel_pkg

    # -------------------------------------------------------------------------
    # Stub FastAPI, its router decorators, and its response types
    # -------------------------------------------------------------------------
    fastapi_pkg = types.ModuleType("fastapi")
    FastAPI = type("FastAPI", (), {
        "add_middleware": lambda self, *args, **kwargs: None,
        "post": classmethod(lambda cls, path: (lambda fn: fn)),
        "get": classmethod(lambda cls, path, **kwargs: (lambda fn: fn)),
        "delete": classmethod(lambda cls, path: (lambda fn: fn)),
    })
    HTTPException = type("HTTPException", (), {})
    Request = type("Request", (), {"headers": {}, "url": types.SimpleNamespace(path="/")})
    Query = lambda *args, **kwargs: None
    fastapi_pkg.FastAPI = FastAPI
    fastapi_pkg.HTTPException = HTTPException
    fastapi_pkg.Request = Request
    fastapi_pkg.Query = Query

    # Stub fastapi.responses
    fastapi_resp_pkg = types.ModuleType("fastapi.responses")
    fastapi_resp_pkg.JSONResponse = lambda *args, **kwargs: types.SimpleNamespace(status_code=kwargs.get("status_code", 200), content=args[0] if args else {})
    fastapi_resp_pkg.PlainTextResponse = lambda *args, **kwargs: types.SimpleNamespace(status_code=kwargs.get("status_code", 200), content=(args[0] if args else ""))
    sys.modules["fastapi"] = fastapi_pkg
    sys.modules["fastapi.responses"] = fastapi_resp_pkg

    # Stub fastapi.middleware.cors.CORSMiddleware
    fastapi_mw_pkg = types.ModuleType("fastapi.middleware")
    cors_pkg = types.ModuleType("fastapi.middleware.cors")
    cors_pkg.CORSMiddleware = type("CORSMiddleware", (), {})
    fastapi_mw_pkg.cors = cors_pkg
    sys.modules["fastapi.middleware"] = fastapi_mw_pkg
    sys.modules["fastapi.middleware.cors"] = cors_pkg

    # -------------------------------------------------------------------------
    # Stub kernel_agents.agent_factory.AgentFactory
    # -------------------------------------------------------------------------
    ka_pkg = types.ModuleType("kernel_agents")
    agent_factory_mod = types.ModuleType("kernel_agents.agent_factory")
    class DummyAgentFactory:
        @staticmethod
        async def create_all_agents(session_id, user_id, memory_store, client=None):
            # returning a mapping so that approve_step logic can do something
            return {"gcm": DummyAgent(), "human": DummyAgent()}

        @staticmethod
        async def create_agent(**kwargs):
            return DummyAgent()

        @staticmethod
        def clear_cache():
            pass

    agent_factory_mod.AgentFactory = DummyAgentFactory
    ka_pkg.agent_factory = agent_factory_mod
    sys.modules["kernel_agents"] = ka_pkg
    sys.modules["kernel_agents.agent_factory"] = agent_factory_mod

    # -------------------------------------------------------------------------
    # Stub middleware.health_check.HealthCheckMiddleware
    # -------------------------------------------------------------------------
    mw_pkg = types.ModuleType("middleware")
    health_mod = types.ModuleType("middleware.health_check")
    class DummyHealthCheckMiddleware:
        def __init__(self, app, password=None, checks=None):
            pass
    health_mod.HealthCheckMiddleware = DummyHealthCheckMiddleware
    mw_pkg.health_check = health_mod
    sys.modules["middleware"] = mw_pkg
    sys.modules["middleware.health_check"] = health_mod

    # -------------------------------------------------------------------------
    # Stub models.messages_kernel (for InputTask, etc.)
    # -------------------------------------------------------------------------
    models_pkg = types.ModuleType("models")
    msgs_mod = types.ModuleType("models.messages_kernel")

    class DummyModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self):
            # Return a minimal plan‐like dict
            return {"id": "planid", "session_id": self.session_id, "initial_goal": self.initial_goal, "overall_status": self.overall_status}

    from enum import Enum
    class DummyAgentType(Enum):
        GROUP_CHAT_MANAGER = "gcm"
        HUMAN = "human"
    msgs_mod.AgentType = DummyAgentType
    msgs_mod.ActionRequest = DummyModel
    msgs_mod.ActionResponse = DummyModel
    msgs_mod.AgentMessage = DummyModel
    msgs_mod.HumanClarification = DummyModel
    msgs_mod.HumanFeedback = DummyModel
    msgs_mod.InputTask = DummyModel
    msgs_mod.Plan = DummyModel
    msgs_mod.PlanWithSteps = DummyModel
    msgs_mod.Step = DummyModel

    models_pkg.messages_kernel = msgs_mod
    sys.modules["models"] = models_pkg
    sys.modules["models.messages_kernel"] = msgs_mod

    # -------------------------------------------------------------------------
    # Stub utils_kernel (initialize_runtime_and_context, get_agents, rai_success)
    # -------------------------------------------------------------------------
    uk_pkg = types.ModuleType("utils_kernel")

    async def fake_initialize_runtime_and_context(session_id=None, user_id=None):
        if not user_id:
            raise ValueError("no user")
        return ("kernel_obj", DummyCosmosContext(session_id=session_id, user_id=user_id))

    uk_pkg.initialize_runtime_and_context = fake_initialize_runtime_and_context

    # get_agents: return a cached dict
    from collections import OrderedDict
    agent_instances = OrderedDict()

    async def fake_get_agents(session_id, user_id):
        if (session_id, user_id) not in agent_instances:
            agent_instances[(session_id, user_id)] = {"gcm": DummyAgent()}
        return agent_instances[(session_id, user_id)]

    uk_pkg.get_agents = fake_get_agents

    async def fake_rai_success(description):
        return True

    uk_pkg.rai_success = fake_rai_success

    sys.modules["utils_kernel"] = uk_pkg

    # -------------------------------------------------------------------------
    # stub any other Azure imports
    # -------------------------------------------------------------------------
    azure_identity_pkg = types.ModuleType("azure.identity.aio")
    azure_identity_pkg.DefaultAzureCredential = lambda : None
    sys.modules["azure.identity.aio"] = azure_identity_pkg

    # -------------------------------------------------------------------------
    # Stub a “Dummy” agent class
    # -------------------------------------------------------------------------
    class DummyAgent:
        async def handle_input_task(self, input_task):
            return {"handled": True}

        async def handle_human_feedback(self, human_feedback):
            return None

        async def handle_human_clarification(self, human_clarification):
            return None

    # Expose DummyAgent for completeness
    sys.modules["__dummy_agent__"] = types.ModuleType("__dummy_agent__")
    sys.modules["__dummy_agent__"].DummyAgent = DummyAgent

    # -------------------------------------------------------------------------
    # Stub AzureAIAgent for create_azure_ai_agent test
    # -------------------------------------------------------------------------
    class DummyAzureAIAgent:
        def __init__(self, client=None, definition=None, plugins=None):
            self.client = client
            self.definition = definition
            self.plugins = plugins

    sys.modules["__dummy_az_ai_agent__"] = types.ModuleType("__dummy_az_ai_agent__")
    sys.modules["__dummy_az_ai_agent__"].AzureAIAgent = DummyAzureAIAgent

    yield


def test_import_app_kernel_and_has_app():
    """
    After stubbing, importing backend.app_kernel should succeed and expose `app`.
    """
    module = importlib.import_module("backend.app_kernel")
    assert hasattr(module, "app"), "backend.app_kernel should expose an 'app' object"


@pytest.mark.asyncio
async def test_delete_all_messages_returns_status(monkeypatch):
    """
    Simulate delete_all_messages(request) for a valid user_id. Should return {"status": "All messages deleted"}.
    """
    # Ensure auth returns a valid user
    app_mod = importlib.import_module("backend.app_kernel")
    # Create a fake Request with headers
    fake_req = types.SimpleNamespace(headers={"user_principal_id": "u123"})
    # Call delete_all_messages
    response = await app_mod.delete_all_messages(request=fake_req)
    assert isinstance(response, dict)
    assert response.get("status") == "All messages deleted"


def test_routes_exist_on_app():
    """
    Simply verify that the FastAPI `app` object has the correct endpoints attached.
    We check that the route functions exist on the module; actual routing tests
    would require TestClient. Here we merely confirm that the decorated functions
    are present as attributes in backend.app_kernel.
    """
    app_mod = importlib.import_module("backend.app_kernel")

    # Check that each endpoint function is defined in the module
    expected_endpoints = [
        "input_task_endpoint",
        "human_feedback_endpoint",
        "human_clarification_endpoint",
        "approve_step_endpoint",
        "get_plans",
        "get_steps_by_plan",
        "get_agent_messages",
        "delete_all_messages",
        "get_all_messages",
        "get_agent_tools",
    ]
    for fn_name in expected_endpoints:
        assert hasattr(app_mod, fn_name), f"{fn_name} should be defined in backend.app_kernel"


@pytest.mark.asyncio
async def test_input_task_endpoint_bad_user(monkeypatch):
    """
    If get_authenticated_user_details returns no user_id -> input_task_endpoint should raise HTTPException.
    """
    # Re‐stub auth to return empty user
    auth_mod = sys.modules["auth.auth_utils"]
    auth_mod.get_authenticated_user_details = lambda headers: {"user_principal_id": ""}
    app_mod = importlib.import_module("backend.app_kernel")
    # Create a dummy InputTask with minimal attributes
    DummyInputTask = sys.modules["models.messages_kernel"].InputTask
    fake_task = DummyInputTask(
        description="desc",
        session_id=None,
    )
    fake_req = types.SimpleNamespace(headers={})

    with pytest.raises(Exception):
        # Should raise HTTPException since user_principal_id == ""
        await app_mod.input_task_endpoint(fake_task, fake_req)



# -------------------------------------------------------------------------
# Dummy classes used above
# -------------------------------------------------------------------------
class DummyCosmosDB:
    def __init__(self, ident):
        self._ident = ident

class DummyAzureAIAgent:
    pass

class DummyAgent:
    pass

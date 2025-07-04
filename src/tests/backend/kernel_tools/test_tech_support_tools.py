import sys
import types
import pytest
import json

# --- stub out semantic_kernel.functions.kernel_function decorator ---
sk_pkg = types.ModuleType("semantic_kernel")
sk_pkg.__path__ = []
sk_funcs = types.ModuleType("semantic_kernel.functions")
def kernel_function(name=None, description=None):
    def decorator(func):
        setattr(func, "__kernel_function__", True)
        setattr(func, "__kernel_name__", name or func.__name__)
        setattr(func, "__kernel_description__", description)
        return func
    return decorator
sk_funcs.kernel_function = kernel_function
sys.modules["semantic_kernel"] = sk_pkg
sys.modules["semantic_kernel.functions"] = sk_funcs

# --- stub out models.messages_kernel.AgentType ---
models_pkg = types.ModuleType("models")
msgs_mod = types.ModuleType("models.messages_kernel")
from enum import Enum
class AgentType(Enum):
    TECH_SUPPORT = "tech_support_agent"
msgs_mod.AgentType = AgentType
models_pkg.messages_kernel = msgs_mod
sys.modules["models"] = models_pkg
sys.modules["models.messages_kernel"] = msgs_mod

# ensure our src/ is on PYTHONPATH
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# now import the class under test
from backend.kernel_tools.tech_support_tools import TechSupportTools

# parameterize over each async tool method
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method_name, args, expected_heading",
    [
        ("send_welcome_email", ("Alice", "alice@example.com"), "##### Welcome Email Sent"),
        ("set_up_office_365_account", ("Bob", "bob@contoso.com"), "##### Office 365 Account Setup"),
        ("configure_laptop", ("Carol", "XPS 13"), "##### Laptop Configuration"),
        ("reset_password", ("Dave",), "##### Password Reset"),
        ("setup_vpn_access", ("Eve",), "##### VPN Access Setup"),
        ("troubleshoot_network_issue", ("Slow WIFI",), "##### Network Issue Resolved"),
        ("install_software", ("Frank", "VSCode"), "##### Software Installation"),
        ("update_software", ("Grace", "Zoom"), "##### Software Update"),
        ("manage_data_backup", ("Heidi",), "##### Data Backup Managed"),
        ("handle_cybersecurity_incident", ("Malware detected",), "##### Cybersecurity Incident Handled"),
        ("support_procurement_tech", ("Laptop specs",), "##### Technical Specifications Provided"),
        ("collaborate_code_deployment", ("ProjectX",), "##### Code Deployment Collaboration"),
        ("assist_marketing_tech", ("SummerCampaign",), "##### Tech Support for Marketing Campaign"),
        ("assist_product_launch", ("ProductY",), "##### Tech Support for Product Launch"),
        ("implement_it_policy", ("PasswordPolicy",), "##### IT Policy Implemented"),
        ("manage_cloud_service", ("AzureBlob",), "##### Cloud Service Managed"),
        ("configure_server", ("Server1",), "##### Server Configuration"),
        ("grant_database_access", ("Ivan", "DB1"), "##### Database Access Granted"),
        ("provide_tech_training", ("Judy", "Docker"), "##### Tech Training Provided"),
        ("resolve_technical_issue", ("App crash at launch",), "##### Technical Issue Resolved"),
        ("configure_printer", ("Ken", "LaserJet"), "##### Printer Configuration"),
        ("set_up_email_signature", ("Laura", "Best Regards"), "##### Email Signature Setup"),
        ("configure_mobile_device", ("Mallory", "iPhone X"), "##### Mobile Device Configuration"),
        ("manage_software_licenses", ("Photoshop", 5), "##### Software Licenses Managed"),
        ("set_up_remote_desktop", ("Nick",), "##### Remote Desktop Setup"),
        ("troubleshoot_hardware_issue", ("Battery not charging",), "##### Hardware Issue Resolved"),
        ("manage_network_security", (), "##### Network Security Managed"),
    ],
)
async def test_tool_methods(method_name, args, expected_heading):
    method = getattr(TechSupportTools, method_name)
    result = await method(*args)
    # heading present
    assert expected_heading in result
    # formatting instructions appended
    assert TechSupportTools.formatting_instructions in result

def test_get_all_kernel_functions():
    funcs = TechSupportTools.get_all_kernel_functions()
    # must include at least one known tool
    assert "send_welcome_email" in funcs
    assert callable(funcs["send_welcome_email"])

def test_generate_tools_json_doc():
    doc = TechSupportTools.generate_tools_json_doc()
    tools = json.loads(doc)
    # ensure reset_password shows up
    assert any(t["function"] == "reset_password" for t in tools)
    # pick one entry and check it has arguments key
    entry = next(t for t in tools if t["function"] == "grant_database_access")
    assert "employee_name" in entry["arguments"]
    assert "database_name" in entry["arguments"]

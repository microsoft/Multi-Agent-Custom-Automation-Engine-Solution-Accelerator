import os
import sys
import types
import pytest

# --- Stub out semantic_kernel.functions ---
sk_pkg = types.ModuleType("semantic_kernel")
sk_pkg.__path__ = []
sk_funcs = types.ModuleType("semantic_kernel.functions")

def kernel_function(name=None, description=None):
    class DummyKernelFunction:
        def __init__(self, description):
            self.description = description

    def decorator(func):
        setattr(func, "__kernel_name__", name or func.__name__)
        setattr(func, "__kernel_function__", DummyKernelFunction(description))
        return func
    return decorator

sk_funcs.kernel_function = kernel_function
sys.modules["semantic_kernel"] = sk_pkg
sys.modules["semantic_kernel.functions"] = sk_funcs

# --- Stub out models.messages_kernel.AgentType ---
models_pkg = types.ModuleType("models")
msgs_mod = types.ModuleType("models.messages_kernel")
from enum import Enum
class AgentType(Enum):
    HR = 'hr_agent'
    PROCUREMENT = 'procurement_agent'
    MARKETING = 'marketing_agent'
    PRODUCT = 'product_agent'
    TECH_SUPPORT = 'tech_support_agent'
msgs_mod.AgentType = AgentType
models_pkg.messages_kernel = msgs_mod
sys.modules['models'] = models_pkg
sys.modules['models.messages_kernel'] = msgs_mod

# Ensure 'src' is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from backend.kernel_tools.hr_tools import HrTools

@pytest.mark.asyncio
async def test_schedule_orientation_session():
    result = await HrTools.schedule_orientation_session("John Doe", "2025-05-20")
    assert "Orientation Session Scheduled" in result
    assert "**Employee Name:** John Doe" in result
    assert "**Date:** 2025-05-20" in result

@pytest.mark.asyncio
async def test_assign_mentor():
    result = await HrTools.assign_mentor("Jane Doe")
    assert "Mentor Assigned" in result
    assert "**Employee Name:** Jane Doe" in result

@pytest.mark.asyncio
async def test_register_for_benefits():
    result = await HrTools.register_for_benefits("John Doe")
    assert "Benefits Registration" in result
    assert "**Employee Name:** John Doe" in result

@pytest.mark.asyncio
async def test_enroll_in_training_program():
    result = await HrTools.enroll_in_training_program("John Doe", "Leadership Training")
    assert "Training Program Enrollment" in result
    assert "**Employee Name:** John Doe" in result
    assert "**Program Name:** Leadership Training" in result

@pytest.mark.asyncio
async def test_process_leave_request():
    result = await HrTools.process_leave_request("John Doe", "Vacation", "2025-06-01", "2025-06-10")
    assert "Leave Request Processed" in result
    assert "**Leave Type:** Vacation" in result
    assert "**Start Date:** 2025-06-01" in result
    assert "**End Date:** 2025-06-10" in result

# Additional positive and negative test cases for 100% coverage

@pytest.mark.asyncio
async def test_schedule_orientation_session_empty_name():
    result = await HrTools.schedule_orientation_session("", "2025-05-20")
    assert "Orientation Session Scheduled" in result
    assert "**Employee Name:** " in result

@pytest.mark.asyncio
async def test_assign_mentor_empty_name():
    result = await HrTools.assign_mentor("")
    assert "Mentor Assigned" in result
    assert "**Employee Name:** " in result

@pytest.mark.asyncio
async def test_register_for_benefits_empty_name():
    result = await HrTools.register_for_benefits("")
    assert "Benefits Registration" in result
    assert "**Employee Name:** " in result

@pytest.mark.asyncio
async def test_enroll_in_training_program_empty_program():
    result = await HrTools.enroll_in_training_program("John Doe", "")
    assert "Training Program Enrollment" in result
    assert "**Program Name:** " in result

@pytest.mark.asyncio
async def test_process_leave_request_invalid_dates():
    # End date before start date (negative scenario)
    result = await HrTools.process_leave_request("John Doe", "Sick", "2025-06-10", "2025-06-01")
    assert "Leave Request Processed" in result
    assert "**Start Date:** 2025-06-10" in result
    assert "**End Date:** 2025-06-01" in result

@pytest.mark.asyncio
async def test_process_leave_request_empty_fields():
    result = await HrTools.process_leave_request("", "", "", "")
    assert "Leave Request Processed" in result
    assert "**Employee Name:** " in result
    assert "**Leave Type:** " in result
    assert "**Start Date:** " in result
    assert "**End Date:** " in result


@pytest.mark.asyncio
async def test_send_company_announcement():
    result = await HrTools.send_company_announcement("New Policy", "Please read the updated policy.")
    assert "Company Announcement" in result
    assert "**Subject:** New Policy" in result
    assert "Please read the updated policy." in result

@pytest.mark.asyncio
async def test_issue_bonus_valid_amount():
    result = await HrTools.issue_bonus("John Doe", 1500.75)
    assert "Bonus Issued" in result
    assert "**Amount:** $1500.75" in result

@pytest.mark.asyncio
async def test_issue_bonus_zero_amount():
    result = await HrTools.issue_bonus("John Doe", 0.0)
    assert "**Amount:** $0.00" in result

@pytest.mark.asyncio
async def test_add_emergency_contact():
    result = await HrTools.add_emergency_contact("John Doe", "Jane Doe", "123-456-7890")
    assert "Emergency Contact Added" in result
    assert "**Contact Name:** Jane Doe" in result
    assert "**Contact Phone:** 123-456-7890" in result

@pytest.mark.asyncio
async def test_verify_employment():
    result = await HrTools.verify_employment("Jane Doe")
    assert "Employment Verification" in result
    assert "**Employee Name:** Jane Doe" in result

@pytest.mark.asyncio
async def test_send_email_valid():
    result = await HrTools.send_email("john@example.com")
    assert "Welcome Email Sent" in result
    assert "**Email Address:** john@example.com" in result

@pytest.mark.asyncio
async def test_send_email_empty():
    result = await HrTools.send_email("")
    assert "Welcome Email Sent" in result
    assert "**Email Address:** " in result



def test_get_all_kernel_functions_includes_sample():
    funcs = HrTools.get_all_kernel_functions()
    assert isinstance(funcs, dict)
    assert "schedule_orientation_session" in funcs

def test_generate_tools_json_doc_returns_json():
    json_doc = HrTools.generate_tools_json_doc()
    assert json_doc.startswith("[")
    assert '"function": "schedule_orientation_session"' in json_doc



@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["", "Alice", "A" * 1000])
async def test_schedule_orientation_session_edge_cases(name):
    result = await HrTools.schedule_orientation_session(name, "2025-01-01")
    assert "Orientation Session Scheduled" in result
    assert f"**Employee Name:** {name}" in result


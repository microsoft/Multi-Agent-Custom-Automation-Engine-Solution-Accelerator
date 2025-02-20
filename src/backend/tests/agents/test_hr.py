"""
Test suite for HR-related functions in the backend agents module.

This module contains asynchronous test cases for various HR functions,
including employee orientation, benefits registration, payroll setup, and more.
"""

import os
import sys
from unittest.mock import MagicMock
import pytest

# Set mock environment variables for Azure and CosmosDB
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Mock Azure dependencies
sys.modules["azure.monitor.events.extension"] = MagicMock()

# pylint: disable=C0413
from src.backend.agents.hr import (
    schedule_orientation_session,
    assign_mentor,
    register_for_benefits,
    enroll_in_training_program,
    provide_employee_handbook,
    update_employee_record,
    request_id_card,
    set_up_payroll,
    add_emergency_contact,
    process_leave_request,
    update_policies,
    conduct_exit_interview,
    verify_employment,
    schedule_performance_review,
    approve_expense_claim,
    send_company_announcement,
    fetch_employee_directory,
    initiate_background_check,
    organize_team_building_activity,
    manage_employee_transfer,
    track_employee_attendance,
    organize_health_and_wellness_program,
    facilitate_remote_work_setup,
    manage_retirement_plan,
)
# pylint: enable=C0413


@pytest.mark.asyncio
async def test_schedule_orientation_session():
    """Test scheduling an orientation session."""
    result = await schedule_orientation_session("John Doe", "2025-02-01")
    assert "##### Orientation Session Scheduled" in result
    assert "**Employee Name:** John Doe" in result
    assert "**Date:** 2025-02-01" in result


@pytest.mark.asyncio
async def test_assign_mentor():
    """Test assigning a mentor to an employee."""
    result = await assign_mentor("John Doe")
    assert "##### Mentor Assigned" in result
    assert "**Employee Name:** John Doe" in result


@pytest.mark.asyncio
async def test_register_for_benefits():
    """Test registering an employee for benefits."""
    result = await register_for_benefits("John Doe")
    assert "##### Benefits Registration" in result
    assert "**Employee Name:** John Doe" in result


@pytest.mark.asyncio
async def test_enroll_in_training_program():
    """Test enrolling an employee in a training program."""
    result = await enroll_in_training_program("John Doe", "Leadership 101")
    assert "##### Training Program Enrollment" in result
    assert "**Employee Name:** John Doe" in result
    assert "**Program Name:** Leadership 101" in result


@pytest.mark.asyncio
async def test_provide_employee_handbook():
    """Test providing the employee handbook."""
    result = await provide_employee_handbook("John Doe")
    assert "##### Employee Handbook Provided" in result
    assert "**Employee Name:** John Doe" in result


@pytest.mark.asyncio
async def test_update_employee_record():
    """Test updating an employee record."""
    result = await update_employee_record("John Doe", "Email", "john.doe@example.com")
    assert "##### Employee Record Updated" in result
    assert "**Field Updated:** Email" in result
    assert "**New Value:** john.doe@example.com" in result


@pytest.mark.asyncio
async def test_request_id_card():
    """Test requesting an ID card for an employee."""
    result = await request_id_card("John Doe")
    assert "##### ID Card Request" in result
    assert "**Employee Name:** John Doe" in result


@pytest.mark.asyncio
async def test_set_up_payroll():
    """Test setting up payroll for an employee."""
    result = await set_up_payroll("John Doe")
    assert "##### Payroll Setup" in result
    assert "**Employee Name:** John Doe" in result


@pytest.mark.asyncio
async def test_add_emergency_contact():
    """Test adding an emergency contact for an employee."""
    result = await add_emergency_contact("John Doe", "Jane Doe", "123-456-7890")
    assert "##### Emergency Contact Added" in result
    assert "**Contact Name:** Jane Doe" in result
    assert "**Contact Phone:** 123-456-7890" in result


@pytest.mark.asyncio
async def test_process_leave_request():
    """Test processing a leave request for an employee."""
    result = await process_leave_request(
        "John Doe", "Vacation", "2025-03-01", "2025-03-10"
    )
    assert "##### Leave Request Processed" in result
    assert "**Leave Type:** Vacation" in result
    assert "**Start Date:** 2025-03-01" in result
    assert "**End Date:** 2025-03-10" in result


@pytest.mark.asyncio
async def test_update_policies():
    """Test updating company policies."""
    result = await update_policies("Work From Home Policy", "Updated content")
    assert "##### Policy Updated" in result
    assert "**Policy Name:** Work From Home Policy" in result
    assert "Updated content" in result


@pytest.mark.asyncio
async def test_conduct_exit_interview():
    """Test conducting an exit interview."""
    result = await conduct_exit_interview("John Doe")
    assert "##### Exit Interview Conducted" in result
    assert "**Employee Name:** John Doe" in result


@pytest.mark.asyncio
async def test_verify_employment():
    """Test verifying employment."""
    result = await verify_employment("John Doe")
    assert "##### Employment Verification" in result
    assert "**Employee Name:** John Doe" in result


@pytest.mark.asyncio
async def test_schedule_performance_review():
    """Test scheduling a performance review."""
    result = await schedule_performance_review("John Doe", "2025-04-15")
    assert "##### Performance Review Scheduled" in result
    assert "**Date:** 2025-04-15" in result


@pytest.mark.asyncio
async def test_approve_expense_claim():
    """Test approving an expense claim."""
    result = await approve_expense_claim("John Doe", 500.75)
    assert "##### Expense Claim Approved" in result
    assert "**Claim Amount:** $500.75" in result


@pytest.mark.asyncio
async def test_send_company_announcement():
    """Test sending a company-wide announcement."""
    result = await send_company_announcement(
        "Holiday Schedule", "We will be closed on Christmas."
    )
    assert "##### Company Announcement" in result
    assert "**Subject:** Holiday Schedule" in result
    assert "We will be closed on Christmas." in result


@pytest.mark.asyncio
async def test_fetch_employee_directory():
    """Test fetching the employee directory."""
    result = await fetch_employee_directory()
    assert "##### Employee Directory" in result


@pytest.mark.asyncio
async def test_initiate_background_check():
    """Test initiating a background check."""
    result = await initiate_background_check("John Doe")
    assert "##### Background Check Initiated" in result
    assert "**Employee Name:** John Doe" in result


@pytest.mark.asyncio
async def test_organize_team_building_activity():
    """Test organizing a team-building activity."""
    result = await organize_team_building_activity("Escape Room", "2025-05-01")
    assert "##### Team-Building Activity Organized" in result
    assert "**Activity Name:** Escape Room" in result


@pytest.mark.asyncio
async def test_manage_employee_transfer():
    """Test managing an employee transfer."""
    result = await manage_employee_transfer("John Doe", "Marketing")
    assert "##### Employee Transfer" in result
    assert "**New Department:** Marketing" in result


@pytest.mark.asyncio
async def test_track_employee_attendance():
    """Test tracking employee attendance."""
    result = await track_employee_attendance("John Doe")
    assert "##### Attendance Tracked" in result


@pytest.mark.asyncio
async def test_organize_health_and_wellness_program():
    """Test organizing a health and wellness program."""
    result = await organize_health_and_wellness_program("Yoga Session", "2025-06-01")
    assert "##### Health and Wellness Program Organized" in result
    assert "**Program Name:** Yoga Session" in result


@pytest.mark.asyncio
async def test_facilitate_remote_work_setup():
    """Test facilitating remote work setup."""
    result = await facilitate_remote_work_setup("John Doe")
    assert "##### Remote Work Setup Facilitated" in result
    assert "**Employee Name:** John Doe" in result


@pytest.mark.asyncio
async def test_manage_retirement_plan():
    """Test managing a retirement plan."""
    result = await manage_retirement_plan("John Doe")
    assert "##### Retirement Plan Managed" in result
    assert "**Employee Name:** John Doe" in result

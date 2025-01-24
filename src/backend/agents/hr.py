from typing import List

from autogen_core.base import AgentId
from autogen_core.components import default_subscription
from autogen_core.components.models import AzureOpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool, Tool
from typing_extensions import Annotated

from src.backend.agents.base_agent import BaseAgent
from src.backend.context.cosmos_memory import CosmosBufferedChatCompletionContext

formatting_instructions = "Instructions: returning the output of this function call verbatim to the user in markdown. Then write AGENT SUMMARY: and then include a summary of what you did."


# Define HR tools (functions)
async def schedule_orientation_session(employee_name: str, date: str) -> str:
    return (
        f"##### Orientation Session Scheduled\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Date:** {date}\n\n"
        f"Your orientation session has been successfully scheduled. "
        f"Please mark your calendar and be prepared for an informative session.\n"
        f"{formatting_instructions}"
    )


async def assign_mentor(employee_name: str) -> str:
    return (
        f"##### Mentor Assigned\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"A mentor has been assigned to you. They will guide you through your onboarding process and help you settle into your new role.\n"
        f"{formatting_instructions}"
    )


async def register_for_benefits(employee_name: str) -> str:
    return (
        f"##### Benefits Registration\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"You have been successfully registered for benefits. "
        f"Please review your benefits package and reach out if you have any questions.\n"
        f"{formatting_instructions}"
    )


async def enroll_in_training_program(employee_name: str, program_name: str) -> str:
    return (
        f"##### Training Program Enrollment\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Program Name:** {program_name}\n\n"
        f"You have been enrolled in the training program. "
        f"Please check your email for further details and instructions.\n"
        f"{formatting_instructions}"
    )


async def provide_employee_handbook(employee_name: str) -> str:
    return (
        f"##### Employee Handbook Provided\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"The employee handbook has been provided to you. "
        f"Please review it to familiarize yourself with company policies and procedures.\n"
        f"{formatting_instructions}"
    )


async def update_employee_record(employee_name: str, field: str, value: str) -> str:
    return (
        f"##### Employee Record Updated\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Field Updated:** {field}\n"
        f"**New Value:** {value}\n\n"
        f"Your employee record has been successfully updated.\n"
        f"{formatting_instructions}"
    )


async def request_id_card(employee_name: str) -> str:
    return (
        f"##### ID Card Request\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"Your request for an ID card has been successfully submitted. "
        f"Please allow 3-5 business days for processing. You will be notified once your ID card is ready for pickup.\n"
        f"{formatting_instructions}"
    )


async def set_up_payroll(employee_name: str) -> str:
    return (
        f"##### Payroll Setup\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"Your payroll has been successfully set up. "
        f"Please review your payroll details and ensure everything is correct.\n"
        f"{formatting_instructions}"
    )


async def add_emergency_contact(
    employee_name: str, contact_name: str, contact_phone: str
) -> str:
    return (
        f"##### Emergency Contact Added\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Contact Name:** {contact_name}\n"
        f"**Contact Phone:** {contact_phone}\n\n"
        f"Your emergency contact information has been successfully added.\n"
        f"{formatting_instructions}"
    )


async def process_leave_request(
    employee_name: str, leave_type: str, start_date: str, end_date: str
) -> str:
    return (
        f"##### Leave Request Processed\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Leave Type:** {leave_type}\n"
        f"**Start Date:** {start_date}\n"
        f"**End Date:** {end_date}\n\n"
        f"Your leave request has been processed. "
        f"Please ensure you have completed any necessary handover tasks before your leave.\n"
        f"{formatting_instructions}"
    )


async def update_policies(policy_name: str, policy_content: str) -> str:
    return (
        f"##### Policy Updated\n"
        f"**Policy Name:** {policy_name}\n\n"
        f"The policy has been updated with the following content:\n\n"
        f"{policy_content}\n"
        f"{formatting_instructions}"
    )


async def conduct_exit_interview(employee_name: str) -> str:
    return (
        f"##### Exit Interview Conducted\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"The exit interview has been conducted. "
        f"Thank you for your feedback and contributions to the company.\n"
        f"{formatting_instructions}"
    )


async def verify_employment(employee_name: str) -> str:
    return (
        f"##### Employment Verification\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"The employment status of {employee_name} has been verified.\n"
        f"{formatting_instructions}"
    )


async def schedule_performance_review(employee_name: str, date: str) -> str:
    return (
        f"##### Performance Review Scheduled\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Date:** {date}\n\n"
        f"Your performance review has been scheduled. "
        f"Please prepare any necessary documents and be ready for the review.\n"
        f"{formatting_instructions}"
    )


async def approve_expense_claim(employee_name: str, claim_amount: float) -> str:
    return (
        f"##### Expense Claim Approved\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Claim Amount:** ${claim_amount:.2f}\n\n"
        f"Your expense claim has been approved. "
        f"The amount will be reimbursed in your next payroll.\n"
        f"{formatting_instructions}"
    )


async def send_company_announcement(subject: str, content: str) -> str:
    return (
        f"##### Company Announcement\n"
        f"**Subject:** {subject}\n\n"
        f"{content}\n"
        f"{formatting_instructions}"
    )


async def fetch_employee_directory() -> str:
    return (
        f"##### Employee Directory\n\n"
        f"The employee directory has been retrieved.\n"
        f"{formatting_instructions}"
    )


async def get_hr_information(
    query: Annotated[str, "The query for the HR knowledgebase"]
) -> str:
    information = (
        f"##### HR Information\n\n"
        f"**Document Name:** Contoso's Employee Onboarding Procedure\n"
        f"**Domain:** HR Policy\n"
        f"**Description:** A step-by-step guide detailing the onboarding process for new Contoso employees, from initial orientation to role-specific training.\n"
        f"{formatting_instructions}"
    )
    return information


# Additional HR tools
async def initiate_background_check(employee_name: str) -> str:
    return (
        f"##### Background Check Initiated\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"A background check has been initiated for {employee_name}. "
        f"You will be notified once the check is complete.\n"
        f"{formatting_instructions}"
    )


async def organize_team_building_activity(activity_name: str, date: str) -> str:
    return (
        f"##### Team-Building Activity Organized\n"
        f"**Activity Name:** {activity_name}\n"
        f"**Date:** {date}\n\n"
        f"The team-building activity has been successfully organized. "
        f"Please join us on {date} for a fun and engaging experience.\n"
        f"{formatting_instructions}"
    )


async def manage_employee_transfer(employee_name: str, new_department: str) -> str:
    return (
        f"##### Employee Transfer\n"
        f"**Employee Name:** {employee_name}\n"
        f"**New Department:** {new_department}\n\n"
        f"The transfer has been successfully processed. "
        f"{employee_name} is now part of the {new_department} department.\n"
        f"{formatting_instructions}"
    )


async def track_employee_attendance(employee_name: str) -> str:
    return (
        f"##### Attendance Tracked\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"The attendance for {employee_name} has been successfully tracked.\n"
        f"{formatting_instructions}"
    )


async def organize_health_and_wellness_program(program_name: str, date: str) -> str:
    return (
        f"##### Health and Wellness Program Organized\n"
        f"**Program Name:** {program_name}\n"
        f"**Date:** {date}\n\n"
        f"The health and wellness program has been successfully organized. "
        f"Please join us on {date} for an informative and engaging session.\n"
        f"{formatting_instructions}"
    )


async def facilitate_remote_work_setup(employee_name: str) -> str:
    return (
        f"##### Remote Work Setup Facilitated\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"The remote work setup has been successfully facilitated for {employee_name}. "
        f"Please ensure you have all the necessary equipment and access.\n"
        f"{formatting_instructions}"
    )


async def manage_retirement_plan(employee_name: str) -> str:
    return (
        f"##### Retirement Plan Managed\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"The retirement plan for {employee_name} has been successfully managed.\n"
        f"{formatting_instructions}"
    )


async def handle_overtime_request(employee_name: str, hours: float) -> str:
    return (
        f"##### Overtime Request Handled\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Hours:** {hours}\n\n"
        f"The overtime request for {employee_name} has been successfully handled.\n"
        f"{formatting_instructions}"
    )


async def issue_bonus(employee_name: str, amount: float) -> str:
    return (
        f"##### Bonus Issued\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Amount:** ${amount:.2f}\n\n"
        f"A bonus of ${amount:.2f} has been issued to {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def schedule_wellness_check(employee_name: str, date: str) -> str:
    return (
        f"##### Wellness Check Scheduled\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Date:** {date}\n\n"
        f"A wellness check has been scheduled for {employee_name} on {date}.\n"
        f"{formatting_instructions}"
    )


async def handle_employee_suggestion(employee_name: str, suggestion: str) -> str:
    return (
        f"##### Employee Suggestion Handled\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Suggestion:** {suggestion}\n\n"
        f"The suggestion from {employee_name} has been successfully handled.\n"
        f"{formatting_instructions}"
    )


async def update_employee_privileges(
    employee_name: str, privilege: str, status: str
) -> str:
    return (
        f"##### Employee Privileges Updated\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Privilege:** {privilege}\n"
        f"**Status:** {status}\n\n"
        f"The privileges for {employee_name} have been successfully updated.\n"
        f"{formatting_instructions}"
    )


async def send_email(emailaddress: str) -> str:
    return (
        f"##### Welcome Email Sent\n"
        f"**Email Address:** {emailaddress}\n\n"
        f"A welcome email has been sent to {emailaddress}.\n"
        f"{formatting_instructions}"
    )


# Create the HRTools list
def get_hr_tools() -> List[Tool]:
    return [
        FunctionTool(
            get_hr_information,
            description="Get HR information, such as policies, procedures, and onboarding guidelines.",
        ),
        FunctionTool(
            schedule_orientation_session,
            description="Schedule an orientation session for a new employee.",
        ),
        FunctionTool(assign_mentor, description="Assign a mentor to a new employee."),
        FunctionTool(
            register_for_benefits, description="Register a new employee for benefits."
        ),
        FunctionTool(
            enroll_in_training_program,
            description="Enroll an employee in a training program.",
        ),
        FunctionTool(
            provide_employee_handbook,
            description="Provide the employee handbook to a new employee.",
        ),
        FunctionTool(
            update_employee_record,
            description="Update a specific field in an employee's record.",
        ),
        FunctionTool(
            request_id_card, description="Request an ID card for a new employee."
        ),
        FunctionTool(set_up_payroll, description="Set up payroll for a new employee."),
        FunctionTool(
            add_emergency_contact,
            description="Add an emergency contact for an employee.",
        ),
        FunctionTool(
            process_leave_request,
            description="Process a leave request for an employee.",
        ),
        FunctionTool(update_policies, description="Update a company policy."),
        FunctionTool(
            conduct_exit_interview,
            description="Conduct an exit interview with a departing employee.",
        ),
        FunctionTool(
            verify_employment,
            description="Verify the employment status of an employee.",
        ),
        FunctionTool(
            schedule_performance_review,
            description="Schedule a performance review for an employee.",
        ),
        FunctionTool(
            approve_expense_claim,
            description="Approve an expense claim for an employee.",
        ),
        FunctionTool(
            send_company_announcement, description="Send a company-wide announcement."
        ),
        FunctionTool(
            fetch_employee_directory, description="Fetch the employee directory."
        ),
        FunctionTool(
            initiate_background_check,
            description="Initiate a background check for a new employee.",
        ),
        FunctionTool(
            organize_team_building_activity,
            description="Organize a team-building activity.",
        ),
        FunctionTool(
            manage_employee_transfer,
            description="Manage the transfer of an employee to a new department.",
        ),
        FunctionTool(
            track_employee_attendance,
            description="Track the attendance of an employee.",
        ),
        FunctionTool(
            organize_health_and_wellness_program,
            description="Organize a health and wellness program for employees.",
        ),
        FunctionTool(
            facilitate_remote_work_setup,
            description="Facilitate the setup for remote work for an employee.",
        ),
        FunctionTool(
            manage_retirement_plan,
            description="Manage the retirement plan for an employee.",
        ),
        FunctionTool(
            handle_overtime_request,
            description="Handle an overtime request for an employee.",
        ),
        FunctionTool(issue_bonus, description="Issue a bonus to an employee."),
        FunctionTool(
            schedule_wellness_check,
            description="Schedule a wellness check for an employee.",
        ),
        FunctionTool(
            handle_employee_suggestion,
            description="Handle a suggestion made by an employee.",
        ),
        FunctionTool(
            update_employee_privileges, description="Update privileges for an employee."
        ),
    ]


@default_subscription
class HrAgent(BaseAgent):
    def __init__(
        self,
        model_client: AzureOpenAIChatCompletionClient,
        session_id: str,
        user_id: str,
        memory: CosmosBufferedChatCompletionContext,
        hr_tools: List[Tool],
        hr_tool_agent_id: AgentId,
    ):
        super().__init__(
            "HrAgent",
            model_client,
            session_id,
            user_id,
            memory,
            hr_tools,
            hr_tool_agent_id,
            system_message="You are an AI Agent. You have knowledge about HR (e.g., human resources), policies, procedures, and onboarding guidelines.",
        )

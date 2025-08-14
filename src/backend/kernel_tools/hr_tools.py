import inspect
from typing import Annotated, Callable

from semantic_kernel.functions import kernel_function
from models.messages_kernel import AgentType
import json
from typing import get_type_hints
from app_config import config


class HrTools:
    # Define HR tools (functions)
    selecetd_language = config.get_user_local_browser_language()
    formatting_instructions = "Instructions: returning the output of this function call verbatim to the user in markdown. Then write AGENT SUMMARY: and then include a summary of what you did. Convert all date strings in the following text to short date format with 3-letter month (MMM) in the {selecetd_language} locale (e.g., en-US, en-IN), remove time, and replace original dates with the formatted ones"
    agent_name = AgentType.HR.value

    @staticmethod
    @kernel_function(description="Schedule an orientation session for a new employee.")
    async def schedule_orientation_session(employee_name: str, date: str) -> str:

        return (
            f"##### Orientation Session Scheduled\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Date:** {date}\n\n"
            f"Your orientation session has been successfully scheduled. "
            f"Please mark your calendar and be prepared for an informative session.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Assign a mentor to a new employee.")
    async def assign_mentor(employee_name: str) -> str:
        return (
            f"##### Mentor Assigned\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"A mentor has been assigned to you. They will guide you through your onboarding process and help you settle into your new role.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Register a new employee for benefits.")
    async def register_for_benefits(employee_name: str) -> str:
        return (
            f"##### Benefits Registration\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"You have been successfully registered for benefits. "
            f"Please review your benefits package and reach out if you have any questions.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Enroll an employee in a training program.")
    async def enroll_in_training_program(employee_name: str, program_name: str) -> str:
        return (
            f"##### Training Program Enrollment\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Program Name:** {program_name}\n\n"
            f"You have been enrolled in the training program. "
            f"Please check your email for further details and instructions.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Provide the employee handbook to a new employee.")
    async def provide_employee_handbook(employee_name: str) -> str:
        return (
            f"##### Employee Handbook Provided\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"The employee handbook has been provided to you. "
            f"Please review it to familiarize yourself with company policies and procedures.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Update a specific field in an employee's record.")
    async def update_employee_record(employee_name: str, field: str, value: str) -> str:
        return (
            f"##### Employee Record Updated\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Field Updated:** {field}\n"
            f"**New Value:** {value}\n\n"
            f"Your employee record has been successfully updated.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Request an ID card for a new employee.")
    async def request_id_card(employee_name: str) -> str:
        return (
            f"##### ID Card Request\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"Your request for an ID card has been successfully submitted. "
            f"Please allow 3-5 business days for processing. You will be notified once your ID card is ready for pickup.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Set up payroll for a new employee.")
    async def set_up_payroll(employee_name: str) -> str:
        return (
            f"##### Payroll Setup\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"Your payroll has been successfully set up. "
            f"Please review your payroll details and ensure everything is correct.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Add emergency contact information for an employee.")
    async def add_emergency_contact(
        employee_name: str, contact_name: str, contact_phone: str
    ) -> str:
        return (
            f"##### Emergency Contact Added\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Contact Name:** {contact_name}\n"
            f"**Contact Phone:** {contact_phone}\n\n"
            f"Your emergency contact information has been successfully added.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Process a leave request for an employee.")
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
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Update company policies.")
    async def update_policies(policy_name: str, policy_content: str) -> str:
        return (
            f"##### Policy Updated\n"
            f"**Policy Name:** {policy_name}\n\n"
            f"The policy has been updated with the following content:\n\n"
            f"{policy_content}\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(
        description="Conduct an exit interview for an employee leaving the company."
    )
    async def conduct_exit_interview(employee_name: str) -> str:
        return (
            f"##### Exit Interview Conducted\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"The exit interview has been conducted. "
            f"Thank you for your feedback and contributions to the company.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Verify employment status for an employee.")
    async def verify_employment(employee_name: str) -> str:
        return (
            f"##### Employment Verification\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"The employment status of {employee_name} has been verified.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Schedule a performance review for an employee.")
    async def schedule_performance_review(employee_name: str, date: str) -> str:
        return (
            f"##### Performance Review Scheduled\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Date:** {date}\n\n"
            f"Your performance review has been scheduled. "
            f"Please prepare any necessary documents and be ready for the review.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Approve an expense claim for an employee.")
    async def approve_expense_claim(employee_name: str, claim_amount: float) -> str:
        return (
            f"##### Expense Claim Approved\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Claim Amount:** ${claim_amount:.2f}\n\n"
            f"Your expense claim has been approved. "
            f"The amount will be reimbursed in your next payroll.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Send a company-wide announcement.")
    async def send_company_announcement(subject: str, content: str) -> str:
        return (
            f"##### Company Announcement\n"
            f"**Subject:** {subject}\n\n"
            f"{content}\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Retrieve the employee directory.")
    async def fetch_employee_directory() -> str:
        return (
            f"##### Employee Directory\n\n"
            f"The employee directory has been retrieved.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(
        description="Get HR information, such as policies, procedures, and onboarding guidelines."
    )
    async def get_hr_information(
        query: Annotated[str, "The query for the HR knowledgebase"],
    ) -> str:
        information = (
            f"##### HR Information\n\n"
            f"**Document Name:** Contoso's Employee Onboarding Procedure\n"
            f"**Domain:** HR Policy\n"
            f"**Description:** A step-by-step guide detailing the onboarding process for new Contoso employees, from initial orientation to role-specific training.\n"
            f"{HrTools.formatting_instructions}"
        )
        return information

    # Additional HR tools
    @staticmethod
    @kernel_function(description="Initiate a background check for a new employee.")
    async def initiate_background_check(employee_name: str) -> str:
        return (
            f"##### Background Check Initiated\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"A background check has been initiated for {employee_name}. "
            f"You will be notified once the check is complete.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Organize a team-building activity.")
    async def organize_team_building_activity(activity_name: str, date: str) -> str:
        return (
            f"##### Team-Building Activity Organized\n"
            f"**Activity Name:** {activity_name}\n"
            f"**Date:** {date}\n\n"
            f"The team-building activity has been successfully organized. "
            f"Please join us on {date} for a fun and engaging experience.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage an employee transfer between departments.")
    async def manage_employee_transfer(employee_name: str, new_department: str) -> str:
        return (
            f"##### Employee Transfer\n"
            f"**Employee Name:** {employee_name}\n"
            f"**New Department:** {new_department}\n\n"
            f"The transfer has been successfully processed. "
            f"{employee_name} is now part of the {new_department} department.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Track attendance for an employee.")
    async def track_employee_attendance(employee_name: str) -> str:
        return (
            f"##### Attendance Tracked\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"The attendance for {employee_name} has been successfully tracked.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Organize a health and wellness program.")
    async def organize_wellness_program(program_name: str, date: str) -> str:
        return (
            f"##### Health and Wellness Program Organized\n"
            f"**Program Name:** {program_name}\n"
            f"**Date:** {date}\n\n"
            f"The health and wellness program has been successfully organized. "
            f"Please join us on {date} for an informative and engaging session.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(
        description="Facilitate the setup for remote work for an employee."
    )
    async def facilitate_remote_work_setup(employee_name: str) -> str:
        return (
            f"##### Remote Work Setup Facilitated\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"The remote work setup has been successfully facilitated for {employee_name}. "
            f"Please ensure you have all the necessary equipment and access.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage the retirement plan for an employee.")
    async def manage_retirement_plan(employee_name: str) -> str:
        return (
            f"##### Retirement Plan Managed\n"
            f"**Employee Name:** {employee_name}\n\n"
            f"The retirement plan for {employee_name} has been successfully managed.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Handle an overtime request for an employee.")
    async def handle_overtime_request(employee_name: str, hours: float) -> str:
        return (
            f"##### Overtime Request Handled\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Hours:** {hours}\n\n"
            f"The overtime request for {employee_name} has been successfully handled.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Issue a bonus to an employee.")
    async def issue_bonus(employee_name: str, amount: float) -> str:
        return (
            f"##### Bonus Issued\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Amount:** ${amount:.2f}\n\n"
            f"A bonus of ${amount:.2f} has been issued to {employee_name}.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Schedule a wellness check for an employee.")
    async def schedule_wellness_check(employee_name: str, date: str) -> str:
        return (
            f"##### Wellness Check Scheduled\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Date:** {date}\n\n"
            f"A wellness check has been scheduled for {employee_name} on {date}.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Handle a suggestion made by an employee.")
    async def handle_employee_suggestion(employee_name: str, suggestion: str) -> str:
        return (
            f"##### Employee Suggestion Handled\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Suggestion:** {suggestion}\n\n"
            f"The suggestion from {employee_name} has been successfully handled.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Update privileges for an employee.")
    async def update_employee_privileges(
        employee_name: str, privilege: str, status: str
    ) -> str:
        return (
            f"##### Employee Privileges Updated\n"
            f"**Employee Name:** {employee_name}\n"
            f"**Privilege:** {privilege}\n"
            f"**Status:** {status}\n\n"
            f"The privileges for {employee_name} have been successfully updated.\n"
            f"{HrTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Send a welcome email to an address.")
    async def send_email(emailaddress: str) -> str:
        return (
            f"##### Welcome Email Sent\n"
            f"**Email Address:** {emailaddress}\n\n"
            f"A welcome email has been sent to {emailaddress}.\n"
            f"{HrTools.formatting_instructions}"
        )

    @classmethod
    def get_all_kernel_functions(cls) -> dict[str, Callable]:
        """
        Returns a dictionary of all methods in this class that have the @kernel_function annotation.
        This function itself is not annotated with @kernel_function.

        Returns:
            Dict[str, Callable]: Dictionary with function names as keys and function objects as values
        """
        kernel_functions = {}

        # Get all class methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            # Skip this method itself and any private/special methods
            if name.startswith("_") or name == "get_all_kernel_functions":
                continue

            # Check if the method has the kernel_function annotation
            # by looking at its __annotations__ attribute
            method_attrs = getattr(method, "__annotations__", {})
            if hasattr(method, "__kernel_function__") or "kernel_function" in str(
                method_attrs
            ):
                kernel_functions[name] = method

        return kernel_functions

    @classmethod
    def generate_tools_json_doc(cls) -> str:
        """
        Generate a JSON document containing information about all methods in the class.

        Returns:
            str: JSON string containing the methods' information
        """

        tools_list = []

        # Get all methods from the class that have the kernel_function annotation
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            # Skip this method itself and any private methods
            if name.startswith("_") or name == "generate_tools_json_doc":
                continue

            # Check if the method has the kernel_function annotation
            if hasattr(method, "__kernel_function__"):
                # Get method description from docstring or kernel_function description
                description = ""
                if hasattr(method, "__doc__") and method.__doc__:
                    description = method.__doc__.strip()

                # Get kernel_function description if available
                if hasattr(method, "__kernel_function__") and getattr(
                    method.__kernel_function__, "description", None
                ):
                    description = method.__kernel_function__.description

                # Get argument information by introspection
                sig = inspect.signature(method)
                args_dict = {}

                # Get type hints if available
                type_hints = get_type_hints(method)

                # Process parameters
                for param_name, param in sig.parameters.items():
                    # Skip first parameter 'cls' for class methods (though we're using staticmethod now)
                    if param_name in ["cls", "self"]:
                        continue

                    # Get parameter type
                    param_type = "string"  # Default type
                    if param_name in type_hints:
                        type_obj = type_hints[param_name]
                        # Convert type to string representation
                        if hasattr(type_obj, "__name__"):
                            param_type = type_obj.__name__.lower()
                        else:
                            # Handle complex types like List, Dict, etc.
                            param_type = str(type_obj).lower()
                            if "int" in param_type:
                                param_type = "int"
                            elif "float" in param_type:
                                param_type = "float"
                            elif "bool" in param_type:
                                param_type = "boolean"
                            else:
                                param_type = "string"

                    # Create parameter description
                    # param_desc = param_name.replace("_", " ")
                    args_dict[param_name] = {
                        "description": param_name,
                        "title": param_name.replace("_", " ").title(),
                        "type": param_type,
                    }

                # Add the tool information to the list
                tool_entry = {
                    "agent": cls.agent_name,  # Use HR agent type
                    "function": name,
                    "description": description,
                    "arguments": json.dumps(args_dict).replace('"', "'"),
                }

                tools_list.append(tool_entry)

        # Return the JSON string representation
        return json.dumps(tools_list, ensure_ascii=False, indent=2)

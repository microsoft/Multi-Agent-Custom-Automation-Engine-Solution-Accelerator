from typing import List

from autogen_core.base import AgentId
from autogen_core.components import default_subscription
from autogen_core.components.models import AzureOpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool, Tool
from typing_extensions import Annotated

from src.backend.agents.base_agent import BaseAgent
from src.backend.context.cosmos_memory import CosmosBufferedChatCompletionContext

formatting_instructions = "Instructions: returning the output of this function call verbatim to the user in markdown. Then write AGENT SUMMARY: and then include a summary of what you did."


# Define new Tech tools (functions)
async def send_welcome_email(employee_name: str, email_address: str) -> str:
    """Send a welcome email to a new employee as part of onboarding."""
    return (
        f"##### Welcome Email Sent\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Email Address:** {email_address}\n\n"
        f"A welcome email has been successfully sent to {employee_name} at {email_address}.\n"
        f"{formatting_instructions}"
    )


async def set_up_office_365_account(employee_name: str, email_address: str) -> str:
    """Set up an Office 365 account for an employee."""
    return (
        f"##### Office 365 Account Setup\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Email Address:** {email_address}\n\n"
        f"An Office 365 account has been successfully set up for {employee_name} at {email_address}.\n"
        f"{formatting_instructions}"
    )


async def configure_laptop(employee_name: str, laptop_model: str) -> str:
    """Configure a laptop for a new employee."""
    return (
        f"##### Laptop Configuration\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Laptop Model:** {laptop_model}\n\n"
        f"The laptop {laptop_model} has been successfully configured for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def reset_password(employee_name: str) -> str:
    """Reset the password for an employee."""
    return (
        f"##### Password Reset\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"The password for {employee_name} has been successfully reset.\n"
        f"{formatting_instructions}"
    )


async def setup_vpn_access(employee_name: str) -> str:
    """Set up VPN access for an employee."""
    return (
        f"##### VPN Access Setup\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"VPN access has been successfully set up for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def troubleshoot_network_issue(issue_description: str) -> str:
    """Assist in troubleshooting network issues reported."""
    return (
        f"##### Network Issue Resolved\n"
        f"**Issue Description:** {issue_description}\n\n"
        f"The network issue described as '{issue_description}' has been successfully resolved.\n"
        f"{formatting_instructions}"
    )


async def install_software(employee_name: str, software_name: str) -> str:
    """Install software for an employee."""
    return (
        f"##### Software Installation\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Software Name:** {software_name}\n\n"
        f"The software '{software_name}' has been successfully installed for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def update_software(employee_name: str, software_name: str) -> str:
    """Update software for an employee."""
    return (
        f"##### Software Update\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Software Name:** {software_name}\n\n"
        f"The software '{software_name}' has been successfully updated for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def manage_data_backup(employee_name: str) -> str:
    """Manage data backup for an employee's device."""
    return (
        f"##### Data Backup Managed\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"Data backup has been successfully configured for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def handle_cybersecurity_incident(incident_details: str) -> str:
    """Handle a reported cybersecurity incident."""
    return (
        f"##### Cybersecurity Incident Handled\n"
        f"**Incident Details:** {incident_details}\n\n"
        f"The cybersecurity incident described as '{incident_details}' has been successfully handled.\n"
        f"{formatting_instructions}"
    )


async def assist_procurement_with_tech_equipment(equipment_details: str) -> str:
    """Assist procurement with technical specifications of equipment."""
    return (
        f"##### Technical Specifications Provided\n"
        f"**Equipment Details:** {equipment_details}\n\n"
        f"Technical specifications for the following equipment have been provided: {equipment_details}.\n"
        f"{formatting_instructions}"
    )


async def collaborate_with_code_deployment(project_name: str) -> str:
    """Collaborate with CodeAgent for code deployment."""
    return (
        f"##### Code Deployment Collaboration\n"
        f"**Project Name:** {project_name}\n\n"
        f"Collaboration on the deployment of project '{project_name}' has been successfully completed.\n"
        f"{formatting_instructions}"
    )


async def provide_tech_support_for_marketing(campaign_name: str) -> str:
    """Provide technical support for a marketing campaign."""
    return (
        f"##### Tech Support for Marketing Campaign\n"
        f"**Campaign Name:** {campaign_name}\n\n"
        f"Technical support has been successfully provided for the marketing campaign '{campaign_name}'.\n"
        f"{formatting_instructions}"
    )


async def assist_product_launch(product_name: str) -> str:
    """Provide tech support for a new product launch."""
    return (
        f"##### Tech Support for Product Launch\n"
        f"**Product Name:** {product_name}\n\n"
        f"Technical support has been successfully provided for the product launch of '{product_name}'.\n"
        f"{formatting_instructions}"
    )


async def implement_it_policy(policy_name: str) -> str:
    """Implement and manage an IT policy."""
    return (
        f"##### IT Policy Implemented\n"
        f"**Policy Name:** {policy_name}\n\n"
        f"The IT policy '{policy_name}' has been successfully implemented.\n"
        f"{formatting_instructions}"
    )


async def manage_cloud_service(service_name: str) -> str:
    """Manage cloud services used by the company."""
    return (
        f"##### Cloud Service Managed\n"
        f"**Service Name:** {service_name}\n\n"
        f"The cloud service '{service_name}' has been successfully managed.\n"
        f"{formatting_instructions}"
    )


async def configure_server(server_name: str) -> str:
    """Configure a server."""
    return (
        f"##### Server Configuration\n"
        f"**Server Name:** {server_name}\n\n"
        f"The server '{server_name}' has been successfully configured.\n"
        f"{formatting_instructions}"
    )


async def grant_database_access(employee_name: str, database_name: str) -> str:
    """Grant database access to an employee."""
    return (
        f"##### Database Access Granted\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Database Name:** {database_name}\n\n"
        f"Access to the database '{database_name}' has been successfully granted to {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def provide_tech_training(employee_name: str, tool_name: str) -> str:
    """Provide technical training on new tools."""
    return (
        f"##### Tech Training Provided\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Tool Name:** {tool_name}\n\n"
        f"Technical training on '{tool_name}' has been successfully provided to {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def resolve_technical_issue(issue_description: str) -> str:
    """Resolve general technical issues reported by employees."""
    return (
        f"##### Technical Issue Resolved\n"
        f"**Issue Description:** {issue_description}\n\n"
        f"The technical issue described as '{issue_description}' has been successfully resolved.\n"
        f"{formatting_instructions}"
    )


async def configure_printer(employee_name: str, printer_model: str) -> str:
    """Configure a printer for an employee."""
    return (
        f"##### Printer Configuration\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Printer Model:** {printer_model}\n\n"
        f"The printer '{printer_model}' has been successfully configured for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def set_up_email_signature(employee_name: str, signature: str) -> str:
    """Set up an email signature for an employee."""
    return (
        f"##### Email Signature Setup\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Signature:** {signature}\n\n"
        f"The email signature for {employee_name} has been successfully set up as '{signature}'.\n"
        f"{formatting_instructions}"
    )


async def configure_mobile_device(employee_name: str, device_model: str) -> str:
    """Configure a mobile device for an employee."""
    return (
        f"##### Mobile Device Configuration\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Device Model:** {device_model}\n\n"
        f"The mobile device '{device_model}' has been successfully configured for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def manage_software_licenses(software_name: str, license_count: int) -> str:
    """Manage software licenses for a specific software."""
    return (
        f"##### Software Licenses Managed\n"
        f"**Software Name:** {software_name}\n"
        f"**License Count:** {license_count}\n\n"
        f"{license_count} licenses for the software '{software_name}' have been successfully managed.\n"
        f"{formatting_instructions}"
    )


async def set_up_remote_desktop(employee_name: str) -> str:
    """Set up remote desktop access for an employee."""
    return (
        f"##### Remote Desktop Setup\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"Remote desktop access has been successfully set up for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def troubleshoot_hardware_issue(issue_description: str) -> str:
    """Assist in troubleshooting hardware issues reported."""
    return (
        f"##### Hardware Issue Resolved\n"
        f"**Issue Description:** {issue_description}\n\n"
        f"The hardware issue described as '{issue_description}' has been successfully resolved.\n"
        f"{formatting_instructions}"
    )


async def manage_network_security() -> str:
    """Manage network security protocols."""
    return (
        f"##### Network Security Managed\n\n"
        f"Network security protocols have been successfully managed.\n"
        f"{formatting_instructions}"
    )


async def update_firmware(device_name: str, firmware_version: str) -> str:
    """Update firmware for a specific device."""
    return (
        f"##### Firmware Updated\n"
        f"**Device Name:** {device_name}\n"
        f"**Firmware Version:** {firmware_version}\n\n"
        f"The firmware for '{device_name}' has been successfully updated to version '{firmware_version}'.\n"
        f"{formatting_instructions}"
    )


async def assist_with_video_conferencing_setup(
    employee_name: str, platform: str
) -> str:
    """Assist with setting up video conferencing for an employee."""
    return (
        f"##### Video Conferencing Setup\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Platform:** {platform}\n\n"
        f"Video conferencing has been successfully set up for {employee_name} on the platform '{platform}'.\n"
        f"{formatting_instructions}"
    )


async def manage_it_inventory() -> str:
    """Manage IT inventory records."""
    return (
        f"##### IT Inventory Managed\n\n"
        f"IT inventory records have been successfully managed.\n"
        f"{formatting_instructions}"
    )


async def configure_firewall_rules(rules_description: str) -> str:
    """Configure firewall rules."""
    return (
        f"##### Firewall Rules Configured\n"
        f"**Rules Description:** {rules_description}\n\n"
        f"The firewall rules described as '{rules_description}' have been successfully configured.\n"
        f"{formatting_instructions}"
    )


async def manage_virtual_machines(vm_details: str) -> str:
    """Manage virtual machines."""
    return (
        f"##### Virtual Machines Managed\n"
        f"**VM Details:** {vm_details}\n\n"
        f"Virtual machines have been successfully managed with the following details: {vm_details}.\n"
        f"{formatting_instructions}"
    )


async def provide_tech_support_for_event(event_name: str) -> str:
    """Provide technical support for a company event."""
    return (
        f"##### Tech Support for Event\n"
        f"**Event Name:** {event_name}\n\n"
        f"Technical support has been successfully provided for the event '{event_name}'.\n"
        f"{formatting_instructions}"
    )


async def configure_network_storage(employee_name: str, storage_details: str) -> str:
    """Configure network storage for an employee."""
    return (
        f"##### Network Storage Configured\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Storage Details:** {storage_details}\n\n"
        f"Network storage has been successfully configured for {employee_name} with the following details: {storage_details}.\n"
        f"{formatting_instructions}"
    )


async def set_up_two_factor_authentication(employee_name: str) -> str:
    """Set up two-factor authentication for an employee."""
    return (
        f"##### Two-Factor Authentication Setup\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"Two-factor authentication has been successfully set up for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def troubleshoot_email_issue(employee_name: str, issue_description: str) -> str:
    """Assist in troubleshooting email issues reported."""
    return (
        f"##### Email Issue Resolved\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Issue Description:** {issue_description}\n\n"
        f"The email issue described as '{issue_description}' has been successfully resolved for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def manage_it_helpdesk_tickets(ticket_details: str) -> str:
    """Manage IT helpdesk tickets."""
    return (
        f"##### Helpdesk Tickets Managed\n"
        f"**Ticket Details:** {ticket_details}\n\n"
        f"Helpdesk tickets have been successfully managed with the following details: {ticket_details}.\n"
        f"{formatting_instructions}"
    )


async def provide_tech_support_for_sales_team(project_name: str) -> str:
    """Provide technical support for the sales team."""
    return (
        f"##### Tech Support for Sales Team\n"
        f"**Project Name:** {project_name}\n\n"
        f"Technical support has been successfully provided for the sales team project '{project_name}'.\n"
        f"{formatting_instructions}"
    )


async def handle_software_bug_report(bug_details: str) -> str:
    """Handle a software bug report."""
    return (
        f"##### Software Bug Report Handled\n"
        f"**Bug Details:** {bug_details}\n\n"
        f"The software bug report described as '{bug_details}' has been successfully handled.\n"
        f"{formatting_instructions}"
    )


async def assist_with_data_recovery(employee_name: str, recovery_details: str) -> str:
    """Assist with data recovery for an employee."""
    return (
        f"##### Data Recovery Assisted\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Recovery Details:** {recovery_details}\n\n"
        f"Data recovery has been successfully assisted for {employee_name} with the following details: {recovery_details}.\n"
        f"{formatting_instructions}"
    )


async def manage_system_updates(update_details: str) -> str:
    """Manage system updates and patches."""
    return (
        f"##### System Updates Managed\n"
        f"**Update Details:** {update_details}\n\n"
        f"System updates have been successfully managed with the following details: {update_details}.\n"
        f"{formatting_instructions}"
    )


async def configure_digital_signatures(
    employee_name: str, signature_details: str
) -> str:
    """Configure digital signatures for an employee."""
    return (
        f"##### Digital Signatures Configured\n"
        f"**Employee Name:** {employee_name}\n"
        f"**Signature Details:** {signature_details}\n\n"
        f"Digital signatures have been successfully configured for {employee_name} with the following details: {signature_details}.\n"
        f"{formatting_instructions}"
    )


async def manage_software_deployment(
    software_name: str, deployment_details: str
) -> str:
    """Manage software deployment across the company."""
    return (
        f"##### Software Deployment Managed\n"
        f"**Software Name:** {software_name}\n"
        f"**Deployment Details:** {deployment_details}\n\n"
        f"The software '{software_name}' has been successfully deployed with the following details: {deployment_details}.\n"
        f"{formatting_instructions}"
    )


async def provide_remote_tech_support(employee_name: str) -> str:
    """Provide remote technical support to an employee."""
    return (
        f"##### Remote Tech Support Provided\n"
        f"**Employee Name:** {employee_name}\n\n"
        f"Remote technical support has been successfully provided for {employee_name}.\n"
        f"{formatting_instructions}"
    )


async def manage_network_bandwidth(bandwidth_details: str) -> str:
    """Manage network bandwidth allocation."""
    return (
        f"##### Network Bandwidth Managed\n"
        f"**Bandwidth Details:** {bandwidth_details}\n\n"
        f"Network bandwidth has been successfully managed with the following details: {bandwidth_details}.\n"
        f"{formatting_instructions}"
    )


async def assist_with_tech_documentation(documentation_details: str) -> str:
    """Assist with creating technical documentation."""
    return (
        f"##### Technical Documentation Created\n"
        f"**Documentation Details:** {documentation_details}\n\n"
        f"Technical documentation has been successfully created with the following details: {documentation_details}.\n"
        f"{formatting_instructions}"
    )


async def monitor_system_performance() -> str:
    """Monitor system performance and health."""
    return (
        f"##### System Performance Monitored\n\n"
        f"System performance and health have been successfully monitored.\n"
        f"{formatting_instructions}"
    )


async def manage_software_updates(software_name: str, update_details: str) -> str:
    """Manage updates for a specific software."""
    return f"Updates for {software_name} managed with details: {update_details}."


async def assist_with_system_migration(migration_details: str) -> str:
    """Assist with system migration tasks."""
    return f"System migration assisted with details: {migration_details}."


async def get_tech_information(
    query: Annotated[str, "The query for the tech knowledgebase"]
) -> str:
    """Get technical information, such as IT policies, procedures, and guidelines."""
    # Placeholder information
    information = """
    Document Name: Contoso's IT Policy and Procedure Manual
    Domain: IT Policy
    Description: A comprehensive guide detailing the IT policies and procedures at Contoso, including acceptable use, security protocols, and incident reporting.
    At Contoso, we prioritize the security and efficiency of our IT infrastructure. All employees are required to adhere to the following policies:
    - Use strong passwords and change them every 90 days.
    - Report any suspicious emails to the IT department immediately.
    - Do not install unauthorized software on company devices.
    - Remote access via VPN is allowed only with prior approval.
    """
    return information


# Create the TechTools list
def get_tech_support_tools() -> List[Tool]:
    TechTools: List[Tool] = [
        FunctionTool(
            send_welcome_email,
            description="Send a welcome email to a new employee as part of onboarding.",
            name="send_welcome_email",
        ),
        FunctionTool(
            set_up_office_365_account,
            description="Set up an Office 365 account for an employee.",
            name="set_up_office_365_account",
        ),
        FunctionTool(
            configure_laptop,
            description="Configure a laptop for a new employee.",
            name="configure_laptop",
        ),
        FunctionTool(
            reset_password,
            description="Reset the password for an employee.",
            name="reset_password",
        ),
        FunctionTool(
            setup_vpn_access,
            description="Set up VPN access for an employee.",
            name="setup_vpn_access",
        ),
        FunctionTool(
            troubleshoot_network_issue,
            description="Assist in troubleshooting network issues reported.",
            name="troubleshoot_network_issue",
        ),
        FunctionTool(
            install_software,
            description="Install software for an employee.",
            name="install_software",
        ),
        FunctionTool(
            update_software,
            description="Update software for an employee.",
            name="update_software",
        ),
        FunctionTool(
            manage_data_backup,
            description="Manage data backup for an employee's device.",
            name="manage_data_backup",
        ),
        FunctionTool(
            handle_cybersecurity_incident,
            description="Handle a reported cybersecurity incident.",
            name="handle_cybersecurity_incident",
        ),
        FunctionTool(
            assist_procurement_with_tech_equipment,
            description="Assist procurement with technical specifications of equipment.",
            name="assist_procurement_with_tech_equipment",
        ),
        FunctionTool(
            collaborate_with_code_deployment,
            description="Collaborate with CodeAgent for code deployment.",
            name="collaborate_with_code_deployment",
        ),
        FunctionTool(
            provide_tech_support_for_marketing,
            description="Provide technical support for a marketing campaign.",
            name="provide_tech_support_for_marketing",
        ),
        FunctionTool(
            assist_product_launch,
            description="Provide tech support for a new product launch.",
            name="assist_product_launch",
        ),
        FunctionTool(
            implement_it_policy,
            description="Implement and manage an IT policy.",
            name="implement_it_policy",
        ),
        FunctionTool(
            manage_cloud_service,
            description="Manage cloud services used by the company.",
            name="manage_cloud_service",
        ),
        FunctionTool(
            configure_server,
            description="Configure a server.",
            name="configure_server",
        ),
        FunctionTool(
            grant_database_access,
            description="Grant database access to an employee.",
            name="grant_database_access",
        ),
        FunctionTool(
            provide_tech_training,
            description="Provide technical training on new tools.",
            name="provide_tech_training",
        ),
        FunctionTool(
            resolve_technical_issue,
            description="Resolve general technical issues reported by employees.",
            name="resolve_technical_issue",
        ),
        FunctionTool(
            configure_printer,
            description="Configure a printer for an employee.",
            name="configure_printer",
        ),
        FunctionTool(
            set_up_email_signature,
            description="Set up an email signature for an employee.",
            name="set_up_email_signature",
        ),
        FunctionTool(
            configure_mobile_device,
            description="Configure a mobile device for an employee.",
            name="configure_mobile_device",
        ),
        FunctionTool(
            manage_software_licenses,
            description="Manage software licenses for a specific software.",
            name="manage_software_licenses",
        ),
        FunctionTool(
            set_up_remote_desktop,
            description="Set up remote desktop access for an employee.",
            name="set_up_remote_desktop",
        ),
        FunctionTool(
            troubleshoot_hardware_issue,
            description="Assist in troubleshooting hardware issues reported.",
            name="troubleshoot_hardware_issue",
        ),
        FunctionTool(
            manage_network_security,
            description="Manage network security protocols.",
            name="manage_network_security",
        ),
        FunctionTool(
            update_firmware,
            description="Update firmware for a specific device.",
            name="update_firmware",
        ),
        FunctionTool(
            assist_with_video_conferencing_setup,
            description="Assist with setting up video conferencing for an employee.",
            name="assist_with_video_conferencing_setup",
        ),
        FunctionTool(
            manage_it_inventory,
            description="Manage IT inventory records.",
            name="manage_it_inventory",
        ),
        FunctionTool(
            configure_firewall_rules,
            description="Configure firewall rules.",
            name="configure_firewall_rules",
        ),
        FunctionTool(
            manage_virtual_machines,
            description="Manage virtual machines.",
            name="manage_virtual_machines",
        ),
        FunctionTool(
            provide_tech_support_for_event,
            description="Provide technical support for a company event.",
            name="provide_tech_support_for_event",
        ),
        FunctionTool(
            configure_network_storage,
            description="Configure network storage for an employee.",
            name="configure_network_storage",
        ),
        FunctionTool(
            set_up_two_factor_authentication,
            description="Set up two-factor authentication for an employee.",
            name="set_up_two_factor_authentication",
        ),
        FunctionTool(
            troubleshoot_email_issue,
            description="Assist in troubleshooting email issues reported.",
            name="troubleshoot_email_issue",
        ),
        FunctionTool(
            manage_it_helpdesk_tickets,
            description="Manage IT helpdesk tickets.",
            name="manage_it_helpdesk_tickets",
        ),
        FunctionTool(
            provide_tech_support_for_sales_team,
            description="Provide technical support for the sales team.",
            name="provide_tech_support_for_sales_team",
        ),
        FunctionTool(
            handle_software_bug_report,
            description="Handle a software bug report.",
            name="handle_software_bug_report",
        ),
        FunctionTool(
            assist_with_data_recovery,
            description="Assist with data recovery for an employee.",
            name="assist_with_data_recovery",
        ),
        FunctionTool(
            manage_system_updates,
            description="Manage system updates and patches.",
            name="manage_system_updates",
        ),
        FunctionTool(
            configure_digital_signatures,
            description="Configure digital signatures for an employee.",
            name="configure_digital_signatures",
        ),
        FunctionTool(
            manage_software_deployment,
            description="Manage software deployment across the company.",
            name="manage_software_deployment",
        ),
        FunctionTool(
            provide_remote_tech_support,
            description="Provide remote technical support to an employee.",
            name="provide_remote_tech_support",
        ),
        FunctionTool(
            manage_network_bandwidth,
            description="Manage network bandwidth allocation.",
            name="manage_network_bandwidth",
        ),
        FunctionTool(
            assist_with_tech_documentation,
            description="Assist with creating technical documentation.",
            name="assist_with_tech_documentation",
        ),
        FunctionTool(
            monitor_system_performance,
            description="Monitor system performance and health.",
            name="monitor_system_performance",
        ),
        FunctionTool(
            manage_software_updates,
            description="Manage updates for a specific software.",
            name="manage_software_updates",
        ),
        FunctionTool(
            assist_with_system_migration,
            description="Assist with system migration tasks.",
            name="assist_with_system_migration",
        ),
        FunctionTool(
            get_tech_information,
            description="Get technical information, such as IT policies, procedures, and guidelines.",
            name="get_tech_information",
        ),
    ]
    return TechTools


@default_subscription
class TechSupportAgent(BaseAgent):
    def __init__(
        self,
        model_client: AzureOpenAIChatCompletionClient,
        session_id: str,
        user_id: str,
        memory: CosmosBufferedChatCompletionContext,
        tech_support_tools: List[Tool],
        tech_support_tool_agent_id: AgentId,
    ):
        super().__init__(
            "TechSupportAgent",
            model_client,
            session_id,
            user_id,
            memory,
            tech_support_tools,
            tech_support_tool_agent_id,
            system_message="You are an AI Agent who is knowledgeable about Information Technology. You are able to help with setting up software, accounts, devices, and other IT-related tasks. If you need additional information from the human user asking the question in order to complete a request, ask before calling a function.",
        )

import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from autogen_core.components.tools import FunctionTool

# Mock the azure.monitor.events.extension module globally
sys.modules["azure.monitor.events.extension"] = MagicMock()
# Mock the event_utils module
sys.modules["src.backend.event_utils"] = MagicMock()

# Set environment variables to mock Config dependencies
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

from src.backend.agents.tech_support import (
    send_welcome_email,
    set_up_office_365_account,
    configure_laptop,
    reset_password,
    setup_vpn_access,
    troubleshoot_network_issue,
    install_software,
    update_software,
    manage_data_backup,
    handle_cybersecurity_incident,
    assist_procurement_with_tech_equipment,
    collaborate_with_code_deployment,
    provide_tech_support_for_marketing,
    assist_product_launch,
    implement_it_policy,
    manage_cloud_service,
    configure_server,
    grant_database_access,
    provide_tech_training,
    configure_printer,
    set_up_email_signature,
    configure_mobile_device,
    set_up_remote_desktop,
    troubleshoot_hardware_issue,
    manage_network_security,
    update_firmware,
    assist_with_video_conferencing_setup,
    manage_it_inventory,
    configure_firewall_rules,
    manage_virtual_machines,
    provide_tech_support_for_event,
    configure_network_storage,
    set_up_two_factor_authentication,
    troubleshoot_email_issue,
    manage_it_helpdesk_tickets,
    handle_software_bug_report,
    assist_with_data_recovery,
    manage_system_updates,
    configure_digital_signatures,
    provide_remote_tech_support,
    manage_network_bandwidth,
    assist_with_tech_documentation,
    monitor_system_performance,
    get_tech_support_tools,
)


# Mock Azure DefaultAzureCredential
@pytest.fixture(autouse=True)
def mock_azure_credentials():
    """Mock Azure DefaultAzureCredential for all tests."""
    with patch("azure.identity.aio.DefaultAzureCredential") as mock_cred:
        mock_cred.return_value.get_token = AsyncMock(return_value={"token": "mock-token"})
        yield


@pytest.mark.asyncio
async def test_collaborate_with_code_deployment():
    try:
        result = await collaborate_with_code_deployment("AI Deployment Project")
        assert "Code Deployment Collaboration" in result
        assert "AI Deployment Project" in result
    finally:
        pass  # Add explicit cleanup if required


@pytest.mark.asyncio
async def test_send_welcome_email():
    try:
        result = await send_welcome_email("John Doe", "john.doe@example.com")
        assert "Welcome Email Sent" in result
        assert "John Doe" in result
        assert "john.doe@example.com" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_set_up_office_365_account():
    try:
        result = await set_up_office_365_account("Jane Smith", "jane.smith@example.com")
        assert "Office 365 Account Setup" in result
        assert "Jane Smith" in result
        assert "jane.smith@example.com" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_configure_laptop():
    try:
        result = await configure_laptop("John Doe", "Dell XPS 15")
        assert "Laptop Configuration" in result
        assert "Dell XPS 15" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_reset_password():
    try:
        result = await reset_password("John Doe")
        assert "Password Reset" in result
        assert "John Doe" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_setup_vpn_access():
    try:
        result = await setup_vpn_access("John Doe")
        assert "VPN Access Setup" in result
        assert "John Doe" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_troubleshoot_network_issue():
    try:
        result = await troubleshoot_network_issue("Slow internet")
        assert "Network Issue Resolved" in result
        assert "Slow internet" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_install_software():
    try:
        result = await install_software("Jane Doe", "Adobe Photoshop")
        assert "Software Installation" in result
        assert "Adobe Photoshop" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_update_software():
    try:
        result = await update_software("John Doe", "Microsoft Office")
        assert "Software Update" in result
        assert "Microsoft Office" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_manage_data_backup():
    try:
        result = await manage_data_backup("Jane Smith")
        assert "Data Backup Managed" in result
        assert "Jane Smith" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_handle_cybersecurity_incident():
    try:
        result = await handle_cybersecurity_incident("Phishing email detected")
        assert "Cybersecurity Incident Handled" in result
        assert "Phishing email detected" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_assist_procurement_with_tech_equipment():
    try:
        result = await assist_procurement_with_tech_equipment("Dell Workstation specs")
        assert "Technical Specifications Provided" in result
        assert "Dell Workstation specs" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_provide_tech_support_for_marketing():
    try:
        result = await provide_tech_support_for_marketing("Holiday Campaign")
        assert "Tech Support for Marketing Campaign" in result
        assert "Holiday Campaign" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_assist_product_launch():
    try:
        result = await assist_product_launch("Smartphone X")
        assert "Tech Support for Product Launch" in result
        assert "Smartphone X" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_implement_it_policy():
    try:
        result = await implement_it_policy("Data Retention Policy")
        assert "IT Policy Implemented" in result
        assert "Data Retention Policy" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_manage_cloud_service():
    try:
        result = await manage_cloud_service("AWS S3")
        assert "Cloud Service Managed" in result
        assert "AWS S3" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_configure_server():
    try:
        result = await configure_server("Database Server")
        assert "Server Configuration" in result
        assert "Database Server" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_grant_database_access():
    try:
        result = await grant_database_access("Alice", "SalesDB")
        assert "Database Access Granted" in result
        assert "Alice" in result
        assert "SalesDB" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_provide_tech_training():
    try:
        result = await provide_tech_training("Bob", "VPN Tool")
        assert "Tech Training Provided" in result
        assert "Bob" in result
        assert "VPN Tool" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_configure_printer():
    try:
        result = await configure_printer("Charlie", "HP LaserJet 123")
        assert "Printer Configuration" in result
        assert "Charlie" in result
        assert "HP LaserJet 123" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_set_up_email_signature():
    try:
        result = await set_up_email_signature("Derek", "Best regards, Derek")
        assert "Email Signature Setup" in result
        assert "Derek" in result
        assert "Best regards, Derek" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_configure_mobile_device():
    try:
        result = await configure_mobile_device("Emily", "iPhone 13")
        assert "Mobile Device Configuration" in result
        assert "Emily" in result
        assert "iPhone 13" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_set_up_remote_desktop():
    try:
        result = await set_up_remote_desktop("Frank")
        assert "Remote Desktop Setup" in result
        assert "Frank" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_troubleshoot_hardware_issue():
    try:
        result = await troubleshoot_hardware_issue("Laptop overheating")
        assert "Hardware Issue Resolved" in result
        assert "Laptop overheating" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_manage_network_security():
    try:
        result = await manage_network_security()
        assert "Network Security Managed" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_update_firmware():
    try:
        result = await update_firmware("Router X", "v1.2.3")
        assert "Firmware Updated" in result
        assert "Router X" in result
        assert "v1.2.3" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_assist_with_video_conferencing_setup():
    try:
        result = await assist_with_video_conferencing_setup("Grace", "Zoom")
        assert "Video Conferencing Setup" in result
        assert "Grace" in result
        assert "Zoom" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_manage_it_inventory():
    try:
        result = await manage_it_inventory()
        assert "IT Inventory Managed" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_configure_firewall_rules():
    try:
        result = await configure_firewall_rules("Allow traffic on port 8080")
        assert "Firewall Rules Configured" in result
        assert "Allow traffic on port 8080" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_manage_virtual_machines():
    try:
        result = await manage_virtual_machines("VM: Ubuntu Server")
        assert "Virtual Machines Managed" in result
        assert "VM: Ubuntu Server" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_provide_tech_support_for_event():
    try:
        result = await provide_tech_support_for_event("Annual Tech Summit")
        assert "Tech Support for Event" in result
        assert "Annual Tech Summit" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_configure_network_storage():
    try:
        result = await configure_network_storage("John Doe", "500GB NAS")
        assert "Network Storage Configured" in result
        assert "John Doe" in result
        assert "500GB NAS" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_set_up_two_factor_authentication():
    try:
        result = await set_up_two_factor_authentication("Jane Smith")
        assert "Two-Factor Authentication Setup" in result
        assert "Jane Smith" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_troubleshoot_email_issue():
    try:
        result = await troubleshoot_email_issue("Alice", "Cannot send emails")
        assert "Email Issue Resolved" in result
        assert "Cannot send emails" in result
        assert "Alice" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_manage_it_helpdesk_tickets():
    try:
        result = await manage_it_helpdesk_tickets("Ticket #123: Password reset")
        assert "Helpdesk Tickets Managed" in result
        assert "Password reset" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_handle_software_bug_report():
    try:
        result = await handle_software_bug_report("Critical bug in payroll module")
        assert "Software Bug Report Handled" in result
        assert "Critical bug in payroll module" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_assist_with_data_recovery():
    try:
        result = await assist_with_data_recovery("Jane Doe", "Recover deleted files")
        assert "Data Recovery Assisted" in result
        assert "Jane Doe" in result
        assert "Recover deleted files" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_manage_system_updates():
    try:
        result = await manage_system_updates("Patch CVE-2023-1234")
        assert "System Updates Managed" in result
        assert "Patch CVE-2023-1234" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_configure_digital_signatures():
    try:
        result = await configure_digital_signatures(
            "John Doe", "Company Approved Signature"
        )
        assert "Digital Signatures Configured" in result
        assert "John Doe" in result
        assert "Company Approved Signature" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_provide_remote_tech_support():
    try:
        result = await provide_remote_tech_support("Mark")
        assert "Remote Tech Support Provided" in result
        assert "Mark" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_manage_network_bandwidth():
    try:
        result = await manage_network_bandwidth("Allocate more bandwidth for video calls")
        assert "Network Bandwidth Managed" in result
        assert "Allocate more bandwidth for video calls" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_assist_with_tech_documentation():
    try:
        result = await assist_with_tech_documentation("Documentation for VPN setup")
        assert "Technical Documentation Created" in result
        assert "VPN setup" in result
    finally:
        pass


@pytest.mark.asyncio
async def test_monitor_system_performance():
    try:
        result = await monitor_system_performance()
        assert "System Performance Monitored" in result
    finally:
        pass


def test_get_tech_support_tools():
    tools = get_tech_support_tools()
    assert isinstance(tools, list)
    assert len(tools) > 40  # Ensure all tools are included
    assert all(isinstance(tool, FunctionTool) for tool in tools)

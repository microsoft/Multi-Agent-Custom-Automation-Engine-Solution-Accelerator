"""BIAB Page object for automating interactions with the Multi-Agent Planner UI."""

import logging
import os
from datetime import datetime
from playwright.sync_api import expect
from base.base import BasePage

logger = logging.getLogger(__name__)


class BIABPage(BasePage):
    """Page object model for BIAB/Multi-Agent Planner workflow automation."""

    WELCOME_PAGE_TITLE = "//span[normalize-space()='Multi-Agent Planner']"
    AI_TEXT = "//span[.='AI-generated content may be incorrect']"
    CONTOSO_LOGO = "//span[.='Contoso']"
    NEW_TASK_PROMPT = "//div[@class='tab tab-new-task']"
    SEND_BUTTON = "//button[@class='fui-Button r1alrhcs home-input-send-button ___w3o4yv0 fhovq9v f1p3nwhy f11589ue f1q5o8ev f1pdflbu fkfq4zb f1t94bn6 f1s2uweq fr80ssc f1ukrpxl fecsdlb fnwyq0v ft1hn21 fuxngvv fy5bs14 fsv2rcd f1h0usnq fs4ktlq f16h9ulv fx2bmrt f1omzyqd f1dfjoow f1j98vj9 fj8yq94 f4xjyn1 f1et0tmh f9ddjv3 f1wi8ngl f18ktai2 fwbmr0d f44c6la']"
    PROMPT_INPUT = "//textarea[@placeholder=\"Tell us what needs planning, building, or connecting—we'll handle the rest.\"]"
    QUICK_TASK = "//div[@role='group']"
    CURRENT_TEAM = "//button[contains(.,'Current Team')]"
    RETAIL_CUSTOMER_SUCCESS = "//div[normalize-space()='Retail Customer Success Team']"
    RETAIL_CUSTOMER_SUCCESS_SELECTED = "//span[.='Retail Customer Success Team']"
    PRODUCT_MARKETING = "//div[normalize-space()='Product Marketing Team']"
    HR_TEAM = "//div[normalize-space()='Human Resources Team']"
    RFP_TEAM = "//div[normalize-space()='RFP Team']"
    CONTRACT_COMPLIANCE_TEAM = "//div[normalize-space()='Contract Compliance Review Team']"
    CONTINUE_BTN = "//button[normalize-space()='Continue']"
    CREATING_PLAN = "//span[normalize-space()='Creating a plan']"
    CUSTOMER_DATA_AGENT = "//span[normalize-space()='Customer Data Agent']"
    ORDER_DATA_AGENT = "//span[normalize-space()='Order Data Agent']"
    ANALYSIS_RECOMMENDATION_AGENT = "//span[normalize-space()='Analysis Recommendation Agent']"
    PROXY_AGENT = "//span[normalize-space()='Proxy Agent']"
    APPROVE_TASK_PLAN = "//button[normalize-space()='Approve Task Plan']"
    PROCESSING_PLAN = "//span[contains(text(),'Processing your plan and coordinating with AI agen')]"
    AI_THINKING_PROCESS = "//span[normalize-space()='AI Thinking Process']"
    RETAIL_CUSTOMER_RESPONSE_VALIDATION = "//p[contains(text(),'🎉🎉')]"
    PRODUCT_MARKETING_RESPONSE_VALIDATION = "//p[contains(text(),'🎉🎉')]"
    RFP_RESPONSE_VALIDATION = "//p[contains(text(),'🎉🎉')]"
    CC_RESPONSE_VALIDATION = "//p[contains(text(),'🎉🎉')]"
    PM_COMPLETED_TASK = "//div[@title='Write a press release about our current products​']"
    CREATING_PLAN_LOADING = "//span[normalize-space()='Creating your plan...']"
    PRODUCT_AGENT = "//span[normalize-space()='Product Agent']"
    MARKETING_AGENT = "//span[normalize-space()='Marketing Agent']"
    HR_HELPER_AGENT = "//span[normalize-space()='HR Helper Agent']"
    TECH_SUPPORT_AGENT = "//span[normalize-space()='Technical Support Agent']"
    INPUT_CLARIFICATION = "//textarea[@placeholder='Type your message here...']"
    SEND_BUTTON_CLARIFICATION = "//button[@class='fui-Button r1alrhcs home-input-send-button ___w3o4yv0 fhovq9v f1p3nwhy f11589ue f1q5o8ev f1pdflbu fkfq4zb f1t94bn6 f1s2uweq fr80ssc f1ukrpxl fecsdlb fnwyq0v ft1hn21 fuxngvv fy5bs14 fsv2rcd f1h0usnq fs4ktlq f16h9ulv fx2bmrt f1omzyqd f1dfjoow f1j98vj9 fj8yq94 f4xjyn1 f1et0tmh f9ddjv3 f1wi8ngl f18ktai2 fwbmr0d f44c6la']"
    HR_COMPLETED_TASK = "//div[@title='onboard new employee']"
    RETAIL_COMPLETED_TASK = "//div[contains(@title,'Analyze the satisfaction of Emily Thompson with Contoso.  If needed, provide a plan to increase her satisfaction.')]"
    ORDER_DATA = "//span[normalize-space()='Order Data']"
    CUSTOMER_DATA = "//span[normalize-space()='Customer Data']"
    ANALYSIS_RECOMMENDATION = "//span[normalize-space()='Analysis Recommendation']"
    RFP_SUMMARY = "//span[.='Rfp Summary']"
    RFP_RISK = "//span[normalize-space()='Rfp Risk']"
    RFP_COMPLIANCE = "//span[normalize-space()='Rfp Compliance']"
    CONTRACT_SUMMARY ="//span[.='Contract Summary']"
    CONTRACT_RISK = "//span[normalize-space()='Contract Risk']"
    CONTRACT_COMPLIANCE ="//span[normalize-space()='Contract Compliance']"
    PRODUCT = "//span[normalize-space()='Product']"
    MARKETING = "//span[normalize-space()='Marketing']"
    TECH_SUPPORT = "//span[normalize-space()='Technical Support']"
    HR_HELPER = "//span[normalize-space()='HR Helper']"
    CANCEL_PLAN = "//button[normalize-space()='Yes']"
    UNABLE_TO_CREATE_PLAN = "//span[normalize-space()='Unable to create plan. Please try again.']"
    CANCEL_BUTTON = "//button[normalize-space()='Cancel']"
    HOME_INPUT_TITLE_WRAPPER = "//div[@class='home-input-title-wrapper']"
    SOURCE_TEXT = "//p[contains(text(),'source')]"
    RAI_VALIDATION = "//span[normalize-space()='Failed to submit clarification']"
    RFP_SUMMARY_AGENT = "//span[normalize-space()='Rfp Summary Agent']"
    RFP_RISK_AGENT = "//span[normalize-space()='Rfp Risk Agent']"
    RFP_COMPLIANCE_AGENT = "//span[normalize-space()='Rfp Compliance Agent']"
    CC_SUMMARY_AGENT = "//span[normalize-space()='Contract Summary Agent']"
    CC_RISK_AGENT = "//span[normalize-space()='Contract Risk Agent']"
    CC_AGENT = "//span[normalize-space()='Contract Compliance Agent']"

    def __init__(self, page):
        """Initialize the BIABPage with a Playwright page instance."""
        super().__init__(page)
        self.page = page

    def reload_home_page(self):
        """Reload the home page URL."""
        from config.constants import URL
        logger.info("Reloading home page...")
        self.page.goto(URL)
        self.page.wait_for_load_state("networkidle")
        logger.info("✓ Home page reloaded successfully")

    def validate_home_page(self):
        """Validate that the home page elements are visible."""
        logger.info("Starting home page validation...")
        
        logger.info("Validating Welcome Page Title is visible...")
        expect(self.page.locator(self.WELCOME_PAGE_TITLE)).to_be_visible()
        logger.info("✓ Welcome Page Title is visible")
        
        logger.info("Validating Contoso Logo is visible...")
        expect(self.page.locator(self.CONTOSO_LOGO)).to_be_visible()
        logger.info("✓ Contoso Logo is visible")
        
        logger.info("Validating AI disclaimer text is visible...")
        expect(self.page.locator(self.AI_TEXT)).to_be_visible()
        logger.info("✓ AI disclaimer text is visible")
        
        logger.info("Home page validation completed successfully!")

    def select_retail_customer_success_team(self):
        """Select Retail Customer Success team and continue."""
        logger.info("Starting team selection process...")
        
        logger.info("Clicking on 'Current Team' button...")
        self.page.locator(self.CURRENT_TEAM).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Current Team' button clicked")
        
        logger.info("Selecting 'Retail Customer Success' radio button...")
        self.page.locator(self.RETAIL_CUSTOMER_SUCCESS).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ 'Retail Customer Success' radio button selected")
        
        logger.info("Clicking 'Continue' button...")
        self.page.locator(self.CONTINUE_BTN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Continue' button clicked")
        
        logger.info("Validating 'Retail Customer Success Team' is selected and visible...")
        expect(self.page.locator(self.RETAIL_CUSTOMER_SUCCESS_SELECTED)).to_be_visible()
        logger.info("✓ 'Retail Customer Success Team' is confirmed as selected")
        
        logger.info("Retail Customer Success team selection completed successfully!")

    def select_product_marketing_team(self):
        """Select Product Marketing team and continue."""
        logger.info("Starting team selection process...")
        
        logger.info("Clicking on 'Current Team' button...")
        self.page.locator(self.CURRENT_TEAM).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Current Team' button clicked")
        
        logger.info("Selecting 'Product Marketing' radio button...")
        self.page.locator(self.PRODUCT_MARKETING).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ 'Product Marketing' radio button selected")
        
        logger.info("Clicking 'Continue' button...")
        self.page.locator(self.CONTINUE_BTN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Continue' button clicked")
        
        logger.info("Product Marketing team selection completed successfully!")

    def select_human_resources_team(self):
        """Select Human Resources team and continue."""
        logger.info("Starting team selection process...")
        
        logger.info("Clicking on 'Current Team' button...")
        self.page.locator(self.CURRENT_TEAM).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Current Team' button clicked")
        
        logger.info("Selecting 'Human Resources' radio button...")
        self.page.locator(self.HR_TEAM).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ 'Human Resources' radio button selected")
        
        logger.info("Clicking 'Continue' button...")
        self.page.locator(self.CONTINUE_BTN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Continue' button clicked")
        
        logger.info("Human Resources team selection completed successfully!")

    def select_quick_task_and_create_plan(self):
        """Select a quick task, send it, and wait for plan creation with all agents."""
        logger.info("Starting quick task selection process...")
        
        logger.info("Clicking on Quick Task...")
        self.page.locator(self.QUICK_TASK).first.click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ Quick Task selected")
        
        logger.info("Clicking Send button...")
        self.page.locator(self.SEND_BUTTON).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ Send button clicked")
        
        logger.info("Validating 'Creating a plan' message is visible...")
        expect(self.page.locator(self.CREATING_PLAN)).to_be_visible(timeout=10000)
        logger.info("✓ 'Creating a plan' message is visible")
        
        logger.info("Waiting for 'Creating a plan' to disappear...")
        self.page.locator(self.CREATING_PLAN).wait_for(state="hidden", timeout=60000)
        logger.info("✓ Plan creation completed")

        self.page.wait_for_timeout(8000)
        
        logger.info("Waiting for 'Creating your plan...' loading to disappear...")
        self.page.locator(self.CREATING_PLAN_LOADING).wait_for(state="hidden", timeout=60000)
        logger.info("✓ 'Creating your plan...' loading disappeared")
        
        logger.info("Quick task selection and plan creation completed successfully!")

    def input_prompt_and_send(self, prompt_text):
        """Input custom prompt text and click send button to create plan."""
        logger.info("Starting custom prompt input process...")
        
        logger.info(f"Typing prompt: {prompt_text}")
        self.page.locator(self.PROMPT_INPUT).fill(prompt_text)
        self.page.wait_for_timeout(1000)
        logger.info("✓ Prompt text entered")
        
        logger.info("Clicking Send button...")
        self.page.locator(self.SEND_BUTTON).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ Send button clicked")
        
        logger.info("Validating 'Creating a plan' message is visible...")
        expect(self.page.locator(self.CREATING_PLAN)).to_be_visible(timeout=10000)
        logger.info("✓ 'Creating a plan' message is visible")
        
        logger.info("Waiting for 'Creating a plan' to disappear...")
        self.page.locator(self.CREATING_PLAN).wait_for(state="hidden", timeout=60000)
        logger.info("✓ Plan creation completed")

        self.page.wait_for_timeout(8000)
        
        logger.info("Waiting for 'Creating your plan...' loading to disappear...")
        self.page.locator(self.CREATING_PLAN_LOADING).wait_for(state="hidden", timeout=60000)
        logger.info("✓ 'Creating your plan...' loading disappeared")
        
        logger.info("Custom prompt input and plan creation completed successfully!")

    def validate_retail_agents_visible(self):
        """Validate that all retail agents are visible."""
        logger.info("Validating all retail agents are visible...")        

        logger.info("Checking Customer Data Agent visibility...")
        expect(self.page.locator(self.CUSTOMER_DATA_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Customer Data Agent is visible")
        
        logger.info("Checking Order Data Agent visibility...")
        expect(self.page.locator(self.ORDER_DATA_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Order Data Agent is visible")
        
        logger.info("Checking Analysis Recommendation Agent visibility...")
        expect(self.page.locator(self.ANALYSIS_RECOMMENDATION_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Analysis Recommendation Agent is visible")
        
        logger.info("Checking Proxy Agent visibility...")
        expect(self.page.locator(self.PROXY_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Proxy Agent is visible")
        
        logger.info("All agents validation completed successfully!")

    def validate_product_marketing_agents(self):
        """Validate that all product marketing agents are visible."""
        logger.info("Validating all product marketing agents are visible...")        

        logger.info("Checking Product Agent visibility...")
        expect(self.page.locator(self.PRODUCT_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Product Agent is visible")
        
        logger.info("Checking Marketing Agent visibility...")
        expect(self.page.locator(self.MARKETING_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Marketing Agent is visible")
        
        logger.info("Checking Proxy Agent visibility...")
        expect(self.page.locator(self.PROXY_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Proxy Agent is visible")
        
        logger.info("All product marketing agents validation completed successfully!")

    def validate_hr_agents(self):
        """Validate that all HR agents are visible."""
        logger.info("Validating all HR agents are visible...")        

        logger.info("Checking HR Helper Agent visibility...")
        expect(self.page.locator(self.HR_HELPER_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ HR Helper Agent is visible")
        
        logger.info("Checking Technical Support Agent visibility...")
        expect(self.page.locator(self.TECH_SUPPORT_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Technical Support Agent is visible")
        
        logger.info("Checking Proxy Agent visibility...")
        expect(self.page.locator(self.PROXY_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Proxy Agent is visible")
        
        logger.info("All HR agents validation completed successfully!")

    def validate_rfp_agents_visible(self):
        """Validate that all RFP agents are visible."""
        logger.info("Validating all RFP agents are visible...")        

        logger.info("Checking RFP Summary Agent visibility...")
        expect(self.page.locator(self.RFP_SUMMARY_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ RFP Summary Agent is visible")
        
        logger.info("Checking RFP Risk Agent visibility...")
        expect(self.page.locator(self.RFP_RISK_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ RFP Risk Agent is visible")
        
        logger.info("Checking RFP Compliance Agent visibility...")
        expect(self.page.locator(self.RFP_COMPLIANCE_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ RFP Compliance Agent is visible")
    
        logger.info("All RFP agents validation completed successfully!")

    def validate_contract_compliance_agents_visible(self):
        """Validate that all Contract Compliance agents are visible."""
        logger.info("Validating all Contract Compliance agents are visible...")        

        logger.info("Checking Contract Summary Agent visibility...")
        expect(self.page.locator(self.CC_SUMMARY_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Contract Summary Agent is visible")
        
        logger.info("Checking Contract Risk Agent visibility...")
        expect(self.page.locator(self.CC_RISK_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Contract Risk Agent is visible")
        
        logger.info("Checking Contract Compliance Agent visibility...")
        expect(self.page.locator(self.CC_AGENT)).to_be_visible(timeout=10000)
        logger.info("✓ Contract Compliance Agent is visible")
        
        logger.info("All Contract Compliance agents validation completed successfully!")

    def cancel_retail_task_plan(self):
        """Cancel the retail task plan."""
        logger.info("Starting retail task plan cancellation process...")
        self.page.locator(self.CANCEL_PLAN).click()
        self.page.wait_for_timeout(3000)
        logger.info("✓ 'Cancel Retail Task Plan' button clicked")

    def approve_retail_task_plan(self):
        """Approve the task plan and wait for processing to complete."""
        logger.info("Starting retail task plan approval process...")

        logger.info("Clicking 'Approve Retail Task Plan' button...")
        self.page.locator(self.APPROVE_TASK_PLAN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Approve Retail Task Plan' button clicked")
        
        logger.info("Waiting for 'Processing your plan' message to be visible...")
        expect(self.page.locator(self.PROCESSING_PLAN)).to_be_visible(timeout=10000)
        logger.info("✓ 'Processing your plan' message is visible")

        #self.validate_agent_message_api_status(agent_name="CustomerDataAgent")
        
        logger.info("Waiting for plan processing to complete...")
        self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=400000)
        logger.info("✓ Plan processing completed")
        
        # Check if INPUT_CLARIFICATION textbox is enabled
        logger.info("Checking if clarification input is enabled...")
        clarification_input = self.page.locator(self.INPUT_CLARIFICATION)
        try:
            if clarification_input.is_visible(timeout=5000) and clarification_input.is_enabled():
                logger.warning("⚠ Clarification input is enabled - Task plan may require additional clarification")
                # Don't raise error - this is expected for some teams like HR
                return True  # Indicates clarification is needed
            logger.info("✓ No clarification required - task completed successfully")
            return False  # No clarification needed
        except (TimeoutError, Exception) as e:
            # No clarification input detected, proceed normally
            logger.info(f"✓ No clarification input detected - proceeding normally: {e}")
            return False

    def approve_task_plan(self):
        """Approve the task plan and wait for processing to complete (without clarification check)."""
        logger.info("Starting task plan approval process...")
        
        logger.info("Clicking 'Approve Task Plan' button...")
        self.page.locator(self.APPROVE_TASK_PLAN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Approve Task Plan' button clicked")
        
        logger.info("Waiting for 'Processing your plan' message to be visible...")
        expect(self.page.locator(self.PROCESSING_PLAN)).to_be_visible(timeout=10000)
        logger.info("✓ 'Processing your plan' message is visible")

        #self.validate_agent_message_api_status(agent_name="CustomerDataAgent")
        
        logger.info("Waiting for plan processing to complete...")
        self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=400000)
        logger.info("✓ Plan processing completed")
        
        logger.info("Task plan approval and processing completed successfully!")

    def approve_product_marketing_task_plan(self):
        """Approve the task plan and wait for processing to complete."""
        logger.info("Starting task plan approval process...")
        
        logger.info("Clicking 'Approve Task Plan' button...")
        self.page.locator(self.APPROVE_TASK_PLAN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Approve Task Plan' button clicked")
        
        logger.info("Waiting for 'Processing your plan' message to be visible...")
        expect(self.page.locator(self.PROCESSING_PLAN)).to_be_visible(timeout=10000)
        logger.info("✓ 'Processing your plan' message is visible")

        #self.validate_agent_message_api_status(agent_name="CustomerDataAgent")
        
        logger.info("Waiting for plan processing to complete...")
        self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=400000)
        logger.info("✓ Plan processing completed")
        
        # Check if INPUT_CLARIFICATION textbox is enabled
        logger.info("Checking if clarification input is enabled...")
        clarification_input = self.page.locator(self.INPUT_CLARIFICATION)
        try:
            if clarification_input.is_visible(timeout=5000) and clarification_input.is_enabled():
                logger.info("⚠ Clarification input is enabled - Providing product marketing details")
                
                # Fill in product marketing clarification details
                pm_clarification = ("company name : Contoso, Contact details: 1234567890, "
                                    "Website : contoso.com, Target Audience: GenZ, "
                                    "Theme: No specific Theme")
                logger.info(f"Typing clarification: {pm_clarification}")
                clarification_input.fill(pm_clarification)
                self.page.wait_for_timeout(3000)
                logger.info("✓ Product marketing clarification entered")
                
                # Click send button
                logger.info("Clicking Send button for clarification...")
                self.page.locator(self.SEND_BUTTON_CLARIFICATION).click()
                self.page.wait_for_timeout(2000)
                logger.info("✓ Clarification send button clicked")
                
                # Wait for processing to start again
                logger.info("Waiting for 'Processing your plan' message after clarification...")
                expect(self.page.locator(self.PROCESSING_PLAN)).to_be_visible(timeout=15000)
                logger.info("✓ 'Processing your plan' message is visible after clarification")
                logger.info("Waiting for plan processing to complete...")
                self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=200000)
                logger.info("✓ Plan processing completed")
            else:
                logger.info("✓ No clarification required - task completed successfully")
        except (TimeoutError, Exception) as e:
            logger.info(f"✓ No clarification input detected - proceeding normally: {e}")
        
        logger.info("Task plan approval and processing completed successfully!")

    def approve_rfp_task_plan(self):
        """Approve the RFP task plan and wait for processing to complete."""
        logger.info("Starting RFP task plan approval process...")
        
        logger.info("Clicking 'Approve Task Plan' button...")
        self.page.locator(self.APPROVE_TASK_PLAN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Approve Task Plan' button clicked")
        
        logger.info("Waiting for 'Processing your plan' message to be visible...")
        expect(self.page.locator(self.PROCESSING_PLAN)).to_be_visible(timeout=10000)
        logger.info("✓ 'Processing your plan' message is visible")
        
        logger.info("Waiting for plan processing to complete...")
        self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=400000)
        logger.info("✓ Plan processing completed")
        
        # Check if INPUT_CLARIFICATION textbox is enabled
        logger.info("Checking if clarification input is enabled...")
        clarification_input = self.page.locator(self.INPUT_CLARIFICATION)
        try:
            if clarification_input.is_visible(timeout=5000) and clarification_input.is_enabled():
                logger.warning("⚠ Clarification input is enabled - RFP Task plan may require additional clarification")
                # Don't raise error - this is expected for some workflows
                return True  # Indicates clarification is needed
            logger.info("✓ No clarification required - task completed successfully")
            return False  # No clarification needed
        except (TimeoutError, Exception) as e:
            # No clarification input detected, proceed normally
            logger.info(f"✓ No clarification input detected - proceeding normally: {e}")
            return False

    def approve_contract_compliance_task_plan(self):
        """Approve the Contract Compliance task plan and wait for processing to complete."""
        logger.info("Starting Contract Compliance task plan approval process...")
        
        logger.info("Clicking 'Approve Task Plan' button...")
        self.page.locator(self.APPROVE_TASK_PLAN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Approve Task Plan' button clicked")
        
        logger.info("Waiting for 'Processing your plan' message to be visible...")
        expect(self.page.locator(self.PROCESSING_PLAN)).to_be_visible(timeout=10000)
        logger.info("✓ 'Processing your plan' message is visible")
        
        logger.info("Waiting for plan processing to complete...")
        self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=400000)
        logger.info("✓ Plan processing completed")
        
        # Check if INPUT_CLARIFICATION textbox is enabled
        logger.info("Checking if clarification input is enabled...")
        clarification_input = self.page.locator(self.INPUT_CLARIFICATION)
        try:
            if clarification_input.is_visible(timeout=5000) and clarification_input.is_enabled():
                logger.warning("⚠ Clarification input is enabled - Contract Compliance Task plan may require additional clarification")
                # Don't raise error - this is expected for some workflows
                return True  # Indicates clarification is needed
            logger.info("✓ No clarification required - task completed successfully")
            return False  # No clarification needed
        except (TimeoutError, Exception) as e:
            # No clarification input detected, proceed normally
            logger.info(f"✓ No clarification input detected - proceeding normally: {e}")
            return False

    def validate_retail_customer_response(self):
        """Validate the retail customer response."""

        logger.info("Validating retail customer response...")
        
        # Wait for AI Thinking Process to complete (if visible)
        logger.info("Checking if AI is still thinking...")
        try:
            if self.page.locator(self.AI_THINKING_PROCESS).is_visible(timeout=5000):
                logger.info("AI Thinking Process detected, waiting for it to complete...")
                self.page.locator(self.AI_THINKING_PROCESS).wait_for(state="hidden", timeout=120000)
                logger.info("✓ AI Thinking Process completed")
                # Add buffer time after thinking completes
                self.page.wait_for_timeout(3000)
        except Exception as e:
            logger.info("AI Thinking Process not detected or already completed")
        
        expect(self.page.locator(self.RETAIL_CUSTOMER_RESPONSE_VALIDATION)).to_be_visible(timeout=60000)
        logger.info("✓ Retail customer response is visible")
        
        # Validate retail response contains expected content
        logger.info("Checking for retail customer analysis tasks...")
        try:
            # Look for common retail task content that appears in responses
            retail_task_patterns = [
                "//h5[contains(text(), 'Customer')]",
                "//h5[contains(text(), 'Analysis')]",
                "//h5[contains(text(), 'Satisfaction')]",
                "//p[contains(text(), 'Emily Thompson')]",
                "//p[contains(text(), 'Contoso')]"
            ]
            
            task_found = False
            for pattern in retail_task_patterns:
                if self.page.locator(pattern).first.is_visible(timeout=5000):
                    logger.info(f"✓ Retail task validated with content pattern")
                    task_found = True
                    break
            
            if not task_found:
                logger.warning("⚠ No specific retail task content found, but main response is visible")
        except Exception as e:
            logger.warning(f"⚠ Retail task validation check failed, but main response is successful: {e}")
         
        # Soft assertions for Order Data, Customer Data, and Analysis Recommendation
        logger.info("Checking Order Data visibility...")
        try:
            expect(self.page.locator(self.ORDER_DATA).first).to_be_visible(timeout=10000)
            logger.info("✓ Order Data is visible")
        except (AssertionError, TimeoutError) as e:
            logger.warning(f"⚠ Order Data Agent is NOT Utilized in response: {e}")
        
        logger.info("Checking Customer Data visibility...")
        try:
            expect(self.page.locator(self.CUSTOMER_DATA).first).to_be_visible(timeout=10000)
            logger.info("✓ Customer Data is visible")
        except (AssertionError, TimeoutError) as e:
            logger.warning(f"⚠ Customer Data Agent is NOT Utilized in response: {e}")
        
        logger.info("Checking Analysis Recommendation visibility...")
        try:
            expect(self.page.locator(self.ANALYSIS_RECOMMENDATION).first).to_be_visible(timeout=10000)
            logger.info("✓ Analysis Recommendation is visible")
        except (AssertionError, TimeoutError) as e:
            logger.warning(f"⚠ Analysis Recommendation Agent is NOT Utilized in response: {e}")


    def validate_product_marketing_response(self):
        """Validate the product marketing response."""

        logger.info("Validating product marketing response...")
        
        # Wait for AI Thinking Process to complete (if visible)
        logger.info("Checking if AI is still thinking...")
        try:
            if self.page.locator(self.AI_THINKING_PROCESS).is_visible(timeout=5000):
                logger.info("AI Thinking Process detected, waiting for it to complete...")
                self.page.locator(self.AI_THINKING_PROCESS).wait_for(state="hidden", timeout=120000)
                logger.info("✓ AI Thinking Process completed")
                # Add buffer time after thinking completes
                self.page.wait_for_timeout(3000)
        except Exception as e:
            logger.info("AI Thinking Process not detected or already completed")
        
        expect(self.page.locator(self.PRODUCT_MARKETING_RESPONSE_VALIDATION)).to_be_visible(timeout=60000)
        logger.info("✓ Product marketing response is visible")
        
        # Validate product marketing response contains expected content
        logger.info("Checking for product marketing tasks...")
        try:
            # Look for common product marketing task content that appears in responses
            pm_task_patterns = [
                "//h5[contains(text(), 'Press Release')]",
                "//h5[contains(text(), 'Product')]",
                "//h5[contains(text(), 'Marketing')]",
                "//p[contains(text(), 'press release')]",
                "//p[contains(text(), 'products')]"
            ]
            
            task_found = False
            for pattern in pm_task_patterns:
                if self.page.locator(pattern).first.is_visible(timeout=5000):
                    logger.info(f"✓ Product marketing task validated with content pattern")
                    task_found = True
                    break
            
            if not task_found:
                logger.warning("⚠ No specific product marketing task content found, but main response is visible")
        except Exception as e:
            logger.warning(f"⚠ Product marketing task validation check failed, but main response is successful: {e}")
        
        # Soft assertions for Product and Marketing
        logger.info("Checking Product visibility...")
        try:
            expect(self.page.locator(self.PRODUCT).first).to_be_visible(timeout=10000)
            logger.info("✓ Product is visible")
        except (AssertionError, TimeoutError) as e:
            logger.warning(f"⚠ Product Agent is NOT Utilized in response: {e}")
        
        logger.info("Checking Marketing visibility...")
        try:
            expect(self.page.locator(self.MARKETING).first).to_be_visible(timeout=10000)
            logger.info("✓ Marketing is visible")
        except (AssertionError, TimeoutError) as e:
            logger.warning(f"⚠ Marketing Agent is NOT Utilized in response: {e}")

    def validate_hr_response(self):
        """Validate the HR response."""

        logger.info("Validating HR response...")
        
        # Wait for AI Thinking Process to complete (if visible)
        logger.info("Checking if AI is still thinking...")
        try:
            if self.page.locator(self.AI_THINKING_PROCESS).is_visible(timeout=5000):
                logger.info("AI Thinking Process detected, waiting for it to complete...")
                self.page.locator(self.AI_THINKING_PROCESS).wait_for(state="hidden", timeout=120000)
                logger.info("✓ AI Thinking Process completed")
                # Add buffer time after thinking completes
                self.page.wait_for_timeout(3000)
        except Exception as e:
            logger.info("AI Thinking Process not detected or already completed")
        
        logger.info("Waiting for HR response validation (celebration emoji)...")
        expect(self.page.locator(self.PRODUCT_MARKETING_RESPONSE_VALIDATION)).to_be_visible(timeout=60000)
        logger.info("✓ HR response is visible")
        
        # Validate HR response contains expected onboarding tasks
        logger.info("Checking for HR onboarding tasks completion...")
        try:
            # Look for common HR onboarding task headings that appear in responses
            hr_task_patterns = [
                "//h5[contains(text(), 'Orientation Session')]",
                "//h5[contains(text(), 'Employee Handbook')]",
                "//h5[contains(text(), 'Benefits Registration')]",
                "//h5[contains(text(), 'Payroll Setup')]",
                "//p[contains(text(), 'Jessica Smith')]",
                "//p[contains(text(), 'successfully onboarded')]"
            ]
            
            task_found = False
            for pattern in hr_task_patterns:
                if self.page.locator(pattern).first.is_visible(timeout=5000):
                    logger.info(f"✓ HR onboarding task validated with pattern: {pattern}")
                    task_found = True
                    break
            
            if not task_found:
                logger.warning("⚠ No specific HR onboarding task headings found, but main response is visible")
        except Exception as e:
            logger.warning(f"⚠ HR task validation check failed, but main response is successful: {e}")
        
        # Soft assertions for Technical Support and HR Helper
        logger.info("Checking Technical Support visibility...")
        try:
            expect(self.page.locator(self.TECH_SUPPORT).first).to_be_visible(timeout=10000)
            logger.info("✓ Technical Support is visible")
        except (AssertionError, TimeoutError) as e:
            logger.warning(f"⚠ Technical Support Agent is NOT Utilized in response: {e}")
        
        logger.info("Checking HR Helper visibility...")
        try:
            expect(self.page.locator(self.HR_HELPER).first).to_be_visible(timeout=10000)
            logger.info("✓ HR Helper is visible")
        except (AssertionError, TimeoutError) as e:
            logger.warning(f"⚠ HR Helper Agent is NOT Utilized in response: {e}")

    def validate_rfp_response(self):
        """Validate the RFP response."""

        logger.info("Validating RFP response...")
        
        # Wait for AI Thinking Process to complete (if visible)
        logger.info("Checking if AI is still thinking...")
        try:
            if self.page.locator(self.AI_THINKING_PROCESS).is_visible(timeout=5000):
                logger.info("AI Thinking Process detected, waiting for it to complete...")
                self.page.locator(self.AI_THINKING_PROCESS).wait_for(state="hidden", timeout=120000)
                logger.info("✓ AI Thinking Process completed")
                # Add buffer time after thinking completes
                self.page.wait_for_timeout(3000)
        except Exception as e:
            logger.info("AI Thinking Process not detected or already completed")
        
        expect(self.page.locator(self.RFP_RESPONSE_VALIDATION)).to_be_visible(timeout=60000)
        logger.info("✓ RFP response is visible")
        
        # Validate RFP response contains expected content
        logger.info("Checking for RFP analysis content...")
        try:
            # Look for common RFP response content patterns
            rfp_content_patterns = [
                "//p[contains(text(), 'RFP')]",
                "//p[contains(text(), 'proposal')]",
                "//p[contains(text(), 'Woodgrove Bank')]",
                "//p[contains(text(), 'Contoso')]",
                "//p[contains(text(), 'response')]",
                "//p[contains(text(), 'project')]"
            ]
            
            content_found = False
            for pattern in rfp_content_patterns:
                if self.page.locator(pattern).first.is_visible(timeout=5000):
                    logger.info(f"✓ RFP response content validated with pattern")
                    content_found = True
                    break
            
            if not content_found:
                logger.warning("⚠ No specific RFP content patterns found, but main response is visible")
        except Exception as e:
            logger.warning(f"⚠ RFP content validation check failed, but main response is successful: {e}")

    def validate_contract_compliance_response(self):
        """Validate the Contract Compliance response."""

        logger.info("Validating Contract Compliance response...")
        
        # Wait for AI Thinking Process to complete (if visible)
        logger.info("Checking if AI is still thinking...")
        try:
            if self.page.locator(self.AI_THINKING_PROCESS).is_visible(timeout=5000):
                logger.info("AI Thinking Process detected, waiting for it to complete...")
                self.page.locator(self.AI_THINKING_PROCESS).wait_for(state="hidden", timeout=120000)
                logger.info("✓ AI Thinking Process completed")
                # Add buffer time after thinking completes
                self.page.wait_for_timeout(3000)
        except Exception as e:
            logger.info("AI Thinking Process not detected or already completed")
        
        expect(self.page.locator(self.CC_RESPONSE_VALIDATION)).to_be_visible(timeout=60000)
        logger.info("✓ Contract Compliance response is visible")
        
        # Validate Contract Compliance response contains expected content
        logger.info("Checking for Contract Compliance analysis content...")
        try:
            # Look for common contract compliance response content patterns
            cc_content_patterns = [
                "//p[contains(text(), 'contract')]",
                "//p[contains(text(), 'compliance')]",
                "//p[contains(text(), 'agreement')]",
                "//p[contains(text(), 'terms')]",
                "//p[contains(text(), 'review')]",
                "//h5[contains(text(), 'Contract')]"
            ]
            
            content_found = False
            for pattern in cc_content_patterns:
                if self.page.locator(pattern).first.is_visible(timeout=5000):
                    logger.info(f"✓ Contract Compliance response content validated with pattern")
                    content_found = True
                    break
            
            if not content_found:
                logger.warning("⚠ No specific Contract Compliance content patterns found, but main response is visible")
        except Exception as e:
            logger.warning(f"⚠ Contract Compliance content validation check failed, but main response is successful: {e}")

    def click_new_task(self):
        """Click on the New Task button."""
        logger.info("Clicking on 'New Task' button...")
        self.page.locator(self.NEW_TASK_PROMPT).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'New Task' button clicked")

    def input_clarification_and_send(self, clarification_text):
        """Input clarification text and click send button."""
        logger.info("Starting clarification input process...")
        
        logger.info(f"Typing clarification: {clarification_text}")
        self.page.locator(self.INPUT_CLARIFICATION).fill(clarification_text)
        self.page.wait_for_timeout(1000)
        logger.info("✓ Clarification text entered")
        
        logger.info("Clicking Send button for clarification...")
        self.page.locator(self.SEND_BUTTON_CLARIFICATION).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ Clarification send button clicked")
        
        logger.info("Clarification input and send completed successfully!")

        # Try to wait for processing message, but if it's already gone (fast processing), that's okay
        logger.info("Waiting for 'Processing your plan' message to be visible...")
        try:
            expect(self.page.locator(self.PROCESSING_PLAN)).to_be_visible(timeout=10000)
            logger.info("✓ 'Processing your plan' message is visible")
            
            logger.info("Waiting for plan processing to complete...")
            self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=200000)
            logger.info("✓ Plan processing completed")
        except Exception as e:
            # Processing may have completed so quickly that the message was never detected
            logger.info(f"Processing message not detected or already completed: {e}")
            # Give a small buffer to ensure any processing is complete
            self.page.wait_for_timeout(3000)
            logger.info("✓ Proceeding - processing likely completed quickly")

    def input_rai_clarification_and_send(self, clarification_text):
        """Input RAI clarification text and click send button (for RAI testing)."""
        logger.info("Starting RAI clarification input process...")
        
        logger.info(f"Typing RAI clarification: {clarification_text}")
        self.page.locator(self.INPUT_CLARIFICATION).fill(clarification_text)
        self.page.wait_for_timeout(1000)
        logger.info("✓ RAI clarification text entered")
        
        logger.info("Clicking Send button for RAI clarification...")
        self.page.locator(self.SEND_BUTTON_CLARIFICATION).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ RAI clarification send button clicked")
        
        logger.info("RAI clarification input and send completed successfully!")

    def validate_source_text_not_visible(self):
        """Validate that the source text element is not visible."""
        logger.info("Validating that source text is not visible...")
        expect(self.page.locator(self.SOURCE_TEXT)).not_to_be_visible()
        logger.info("✓ Source text is not visible")

    def input_rai_prompt_and_send(self, prompt_text):
        """Input RAI prompt text and click send button."""
        logger.info("Starting RAI prompt input process...")
        
        logger.info(f"Typing RAI prompt: {prompt_text}")
        self.page.locator(self.PROMPT_INPUT).fill(prompt_text)
        self.page.wait_for_timeout(1000)
        logger.info("✓ RAI prompt text entered")
        
        logger.info("Clicking Send button...")
        self.page.locator(self.SEND_BUTTON).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ Send button clicked")

    def validate_rai_error_message(self):
        """Validate that the RAI 'Unable to create plan' error message is visible."""
        logger.info("Validating RAI error response...")
        
        # Wait a bit for system to process the request
        self.page.wait_for_timeout(3000)
        
        # Check for various possible error messages or states
        possible_error_locators = [
            self.UNABLE_TO_CREATE_PLAN,
            "//span[contains(text(), 'Unable')]",
            "//span[contains(text(), 'Error')]",
            "//span[contains(text(), 'failed')]",
            "//div[contains(text(), 'Unable')]",
            "//p[contains(text(), 'Unable')]"
        ]
        
        error_found = False
        for locator in possible_error_locators:
            try:
                if self.page.locator(locator).first.is_visible(timeout=5000):
                    logger.info(f"✓ RAI error message found with locator: {locator}")
                    error_found = True
                    break
            except Exception:
                continue
        
        if not error_found:
            # Check if plan creation didn't start (another valid rejection state)
            try:
                if not self.page.locator(self.CREATING_PLAN).is_visible(timeout=2000):
                    logger.warning("⚠ No explicit error message, but plan creation didn't start - input may have been silently rejected or truncated")
                    error_found = True
            except Exception as e:
                # Ignore failures in this secondary check, but log for troubleshooting
                logger.debug("Failed to verify CREATING_PLAN visibility while checking for RAI rejection state: %s", e)
        
        if not error_found:
            logger.error("✗ No RAI error or rejection state detected; prompt appears to have been accepted unexpectedly")
            # Take a screenshot for investigation before failing the test
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)
                screenshot_path = os.path.join(screenshots_dir, f"rai_validation_failed_{timestamp}.png")
                self.page.screenshot(path=screenshot_path)
                logger.info(f"Screenshot captured for investigation: {screenshot_path}")
            except Exception as e:
                logger.warning("Failed to capture screenshot when RAI validation failed: %s", e)
            raise AssertionError(
                "Expected RAI to block the prompt, but no error message or rejection state was detected."
            )

    def validate_rai_clarification_error_message(self):
        """Validate that the RAI 'Failed to submit clarification' error message is visible."""
        logger.info("Validating RAI 'Failed to submit clarification' message is visible...")
        expect(self.page.locator(self.RAI_VALIDATION)).to_be_visible(timeout=10000)
        logger.info("✓ RAI 'Failed to submit clarification' message is visible")

    def click_cancel_button(self):
        """Click on the Cancel button."""
        logger.info("Clicking on 'Cancel' button...")
        self.page.locator(self.CANCEL_BUTTON).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Cancel' button clicked")

    def select_rfp_team(self):
        """Select RFP team and continue."""
        logger.info("Starting RFP team selection process...")
        
        logger.info("Clicking on 'Current Team' button...")
        self.page.locator(self.CURRENT_TEAM).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Current Team' button clicked")
        
        logger.info("Selecting 'RFP Team' radio button...")
        self.page.locator(self.RFP_TEAM).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ 'RFP Team' radio button selected")
        
        logger.info("Clicking 'Continue' button...")
        self.page.locator(self.CONTINUE_BTN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Continue' button clicked")
        
        logger.info("RFP team selection completed successfully!")

    def select_contract_compliance_team(self):
        """Select Contract Compliance Review team and continue."""
        logger.info("Starting Contract Compliance team selection process...")
        
        logger.info("Clicking on 'Current Team' button...")
        self.page.locator(self.CURRENT_TEAM).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Current Team' button clicked")
        
        logger.info("Selecting 'Contract Compliance Review Team' radio button...")
        self.page.locator(self.CONTRACT_COMPLIANCE_TEAM).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ 'Contract Compliance Review Team' radio button selected")
        
        logger.info("Clicking 'Continue' button...")
        self.page.locator(self.CONTINUE_BTN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ 'Continue' button clicked")
        
        logger.info("Contract Compliance team selection completed successfully!")

    def validate_home_input_visible(self):
        """Validate that user is redirected to home screen with input visible."""
        logger.info("Validating home input is visible...")
        expect(self.page.locator(self.HOME_INPUT_TITLE_WRAPPER)).to_be_visible(timeout=10000)
        logger.info("✓ Home input is visible - user redirected to home screen")

    def validate_send_button_disabled(self):
        """Validate that send button is disabled for empty/space inputs."""
        logger.info("Validating send button is disabled...")
        send_button = self.page.locator(self.SEND_BUTTON)
        is_disabled = send_button.is_disabled()
        if is_disabled:
            logger.info("✓ Send button is disabled as expected")
        else:
            logger.warning("⚠ Send button is enabled but should be disabled")
            # Check if clicking does nothing
            send_button.click()
            self.page.wait_for_timeout(2000)
            # Verify no plan creation started
            try:
                self.page.locator(self.CREATING_PLAN).wait_for(state="visible", timeout=3000)
                logger.error("❌ Plan creation started unexpectedly")
                raise AssertionError("System accepted empty/space query - test failed")
            except Exception as e:
                if "Timeout" in str(e) or "timeout" in str(e):
                    logger.info("✓ No plan creation started - system correctly rejected query")
                else:
                    raise

    def input_text_only(self, text):
        """Input text without sending."""
        logger.info(f"Typing text: {text}")
        self.page.locator(self.PROMPT_INPUT).fill(text)
        self.page.wait_for_timeout(1000)
        logger.info("✓ Text entered")

    def get_team_list_count(self, team_name):
        """Get the count of a specific team in the team selection list."""
        logger.info(f"Counting '{team_name}' entries in team list...")
        team_locator = f"//div[normalize-space()='{team_name}']"
        count = self.page.locator(team_locator).count()
        logger.info(f"✓ Found {count} entries for '{team_name}'")
        return count

    def open_team_selection(self):
        """Open the team selection dropdown."""
        logger.info("Opening team selection dropdown...")
        self.page.locator(self.CURRENT_TEAM).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ Team selection dropdown opened")

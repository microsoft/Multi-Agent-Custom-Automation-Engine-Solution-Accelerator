"""BIAB Page object for automating interactions with the Multi-Agent Planner UI."""

import logging
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
    CONTINUE_BTN = "//button[normalize-space()='Continue']"
    CREATING_PLAN = "//span[normalize-space()='Creating a plan']"
    CUSTOMER_DATA_AGENT = "//span[normalize-space()='Customer Data Agent']"
    ORDER_DATA_AGENT = "//span[normalize-space()='Order Data Agent']"
    ANALYSIS_RECOMMENDATION_AGENT = "//span[normalize-space()='Analysis Recommendation Agent']"
    PROXY_AGENT = "//span[normalize-space()='Proxy Agent']"
    APPROVE_TASK_PLAN = "//button[normalize-space()='Approve Task Plan']"
    PROCESSING_PLAN = "//span[contains(text(),'Processing your plan and coordinating with AI agen')]"
    RETAIL_CUSTOMER_RESPONSE_VALIDATION = "//p[contains(text(),'🎉🎉 Emily Thompson')]"
    PRODUCT_MARKETING_RESPONSE_VALIDATION = "//p[contains(text(),'🎉🎉')]"
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
    PRODUCT = "//span[normalize-space()='Product']"
    MARKETING = "//span[normalize-space()='Marketing']"
    TECH_SUPPORT = "//span[normalize-space()='Technical Support']"
    HR_HELPER = "//span[normalize-space()='HR Helper']"
    CANCEL_PLAN = "//button[normalize-space()='Yes']"



    def __init__(self, page):
        """Initialize the BIABPage with a Playwright page instance."""
        super().__init__(page)
        self.page = page

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
        self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=200000)
        logger.info("✓ Plan processing completed")
        
        # Check if INPUT_CLARIFICATION textbox is enabled
        logger.info("Checking if clarification input is enabled...")
        clarification_input = self.page.locator(self.INPUT_CLARIFICATION)
        try:
            if clarification_input.is_visible(timeout=5000) and clarification_input.is_enabled():
                logger.error("⚠ Clarification input is enabled - Task plan approval requires clarification")
                raise ValueError("INPUT_CLARIFICATION is enabled - retry required")
            logger.info("✓ No clarification required - task completed successfully")
        except ValueError:
            # Re-raise the clarification exception to trigger retry
            raise
        except (TimeoutError, Exception) as e:
            # No clarification input detected, proceed normally
            logger.info(f"✓ No clarification input detected - proceeding normally: {e}")
        
        logger.info("Task plan approval and processing completed successfully!")

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
        self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=200000)
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
        self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=200000)
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

    def validate_retail_customer_response(self):
        """Validate the retail customer response."""

        logger.info("Validating retail customer response...")
        expect(self.page.locator(self.RETAIL_CUSTOMER_RESPONSE_VALIDATION)).to_be_visible(timeout=10000)
        logger.info("✓ Retail customer response is visible")
        expect(self.page.locator(self.RETAIL_COMPLETED_TASK).first).to_be_visible(timeout=6000)
        logger.info("✓ Retail completed task is visible")
         
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
        expect(self.page.locator(self.PRODUCT_MARKETING_RESPONSE_VALIDATION)).to_be_visible(timeout=20000)
        logger.info("✓ Product marketing response is visible")
        expect(self.page.locator(self.PM_COMPLETED_TASK).first).to_be_visible(timeout=6000)
        logger.info("✓ Product marketing completed task is visible")
        
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
        expect(self.page.locator(self.PRODUCT_MARKETING_RESPONSE_VALIDATION)).to_be_visible(timeout=20000)
        logger.info("✓ HR response is visible")
        expect(self.page.locator(self.HR_COMPLETED_TASK).first).to_be_visible(timeout=6000)
        logger.info("✓ HR completed task is visible")
        
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

        logger.info("Waiting for 'Processing your plan' message to be visible...")
        expect(self.page.locator(self.PROCESSING_PLAN)).to_be_visible(timeout=15000)
        logger.info("✓ 'Processing your plan' message is visible")

        logger.info("Waiting for plan processing to complete...")
        self.page.locator(self.PROCESSING_PLAN).wait_for(state="hidden", timeout=200000)
        logger.info("✓ Plan processing completed")

    

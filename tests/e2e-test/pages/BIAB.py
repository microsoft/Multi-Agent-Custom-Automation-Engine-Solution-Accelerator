"""BIAB Page object for automating interactions with the Multi-Agent Planner UI."""

from playwright.sync_api import expect
from base.base import BasePage


class BIABPage(BasePage):
    """Page object model for BIAB/Multi-Agent Planner workflow automation."""

    WELCOME_PAGE_TITLE = "//span[normalize-space()='Multi-Agent Planner']"
    NEW_TASK_PROMPT = "//textarea[@placeholder='Tell us what needs planning, building, or connecting—we'll handle the rest.']"
    SEND_BUTTON = "//div[@role='toolbar']"
    CREATING_PLAN = "//span[normalize-space()='Creating a plan']"
    TASK_LIST = "//span[contains(text(),'1.')]"
    NEW_TASK = "//span[normalize-space()='New task']"
    MOBILE_PLAN = (
        "//span[normalize-space()='Ask about roaming plans prior to heading overseas.']"
    )
    MOBILE_TASK1 = "//span[contains(text(),'1.')]"
    MOBILE_TASK2 = "//span[contains(text(),'2.')]"
    MOBILE_APPROVE_TASK1 = "i[title='Approve']"
    ADDITIONAL_INFO = "//textarea[@placeholder='Add more info to this task...']"
    ADDITIONAL_INFO_SEND_BUTTON = (
        "//div[@class='plan-chat-input-wrapper']//div//div//div//div[@role='toolbar']"
    )
    STAGES = "//button[@aria-label='Approve']"
    RAI_PROMPT_VALIDATION = "//span[normalize-space()='Failed to create plan']"
    COMPLETED_TASK = "//span[@class='fui-Text ___13vod6f fk6fouc fy9rknc fwrc4pm figsok6 fpgzoln f1w7gpdv f6juhto f1gl81tg f2jf649']"

    def __init__(self, page):
        """Initialize the BIABPage with a Playwright page instance."""
        super().__init__(page)
        self.page = page

    def click_my_task(self):
        """Click on the 'My Task' item in the UI."""
        self.page.locator(self.TASK_LIST).click()
        self.page.wait_for_timeout(10000)

    def enter_aditional_info(self, text):
        """Enter additional info and click the send button."""
        additional_info = self.page.locator(self.ADDITIONAL_INFO)

        if additional_info.is_enabled():
            additional_info.fill(text)
            self.page.wait_for_timeout(5000)
            self.page.locator(self.ADDITIONAL_INFO_SEND_BUTTON).click()
            self.page.wait_for_timeout(5000)

    def click_send_button(self):
        """Click the send button and wait for 'Creating a plan' to disappear."""
        self.page.locator(self.SEND_BUTTON).click()
        expect(self.page.locator("span", has_text="Creating a plan")).to_be_visible()
        self.page.locator("span", has_text="Creating a plan").wait_for(
            state="hidden", timeout=50000
        )
        self.page.wait_for_timeout(2000)

    def validate_rai_validation_message(self):
        """Validate RAI prompt error message visibility."""
        self.page.locator(self.SEND_BUTTON).click()
        self.page.wait_for_timeout(1000)
        expect(self.page.locator(self.RAI_PROMPT_VALIDATION)).to_be_visible(
            timeout=10000
        )
        self.page.wait_for_timeout(3000)

    def click_aditional_send_button(self):
        """Click the additional info send button."""
        self.page.locator(self.ADDITIONAL_INFO_SEND_BUTTON).click()
        self.page.wait_for_timeout(5000)

    def click_new_task(self):
        """Click the 'New Task' button."""
        self.page.locator(self.NEW_TASK).click()
        self.page.wait_for_timeout(5000)

    def click_mobile_plan(self):
        """Click on a specific mobile plan in the task list."""
        self.page.locator(self.MOBILE_PLAN).click()
        self.page.wait_for_timeout(3000)

    def validate_home_page(self):
        """Validate that the home page title is visible."""
        expect(self.page.locator(self.WELCOME_PAGE_TITLE)).to_be_visible()

    def enter_a_question(self, text):
        """Enter a question in the prompt textbox."""
        self.page.get_by_role("textbox", name="Tell us what needs planning,").fill(text)
        self.page.wait_for_timeout(4000)

    def processing_different_stage(self):
        """Process and approve each stage sequentially if present."""
        self.page.wait_for_timeout(3000)
        total_count = self.page.locator(self.STAGES).count()
        if self.page.locator(self.STAGES).count() >= 1:
            for _ in range(self.page.locator(self.STAGES).count()):
                approve_stages = self.page.locator(self.STAGES).nth(0)
                approve_stages.click()
                self.page.wait_for_timeout(2000)
                self.page.locator(
                    "//span[normalize-space()='Step approved successfully']"
                ).wait_for(state="visible", timeout=30000)

                plan_id = BasePage.get_first_plan_id(self)
                BasePage.approve_plan_by_id(self, plan_id)
                self.page.wait_for_timeout(7000)

        expect(self.page.locator(self.COMPLETED_TASK)).to_contain_text(f"{total_count} of {total_count} completed")


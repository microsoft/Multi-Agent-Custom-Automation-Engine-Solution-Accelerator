"""Login Page module for handling authentication via email and password."""

from base.base import BasePage


class LoginPage(BasePage):
    """Page object model for login and Microsoft authentication flow."""

    EMAIL_TEXT_BOX = "//input[@type='email']"
    NEXT_BUTTON = "//input[@type='submit']"
    PASSWORD_TEXT_BOX = "//input[@type='password']"
    SIGNIN_BUTTON = "//input[@id='idSIButton9']"
    YES_BUTTON = "//input[@id='idSIButton9']"
    PERMISSION_ACCEPT_BUTTON = "//input[@type='submit']"

    def __init__(self, page):
        """Initialize the LoginPage with the Playwright page instance."""
        self.page = page

    def authenticate(self, username, password):
        """Login using provided username and password with conditional prompts."""
        self.page.locator(self.EMAIL_TEXT_BOX).fill(username)
        self.page.locator(self.NEXT_BUTTON).click()
        self.page.wait_for_load_state("networkidle")

        self.page.locator(self.PASSWORD_TEXT_BOX).fill(password)
        self.page.locator(self.SIGNIN_BUTTON).click()
        self.page.wait_for_timeout(20000)  # Wait for 20 seconds

        if self.page.locator(self.PERMISSION_ACCEPT_BUTTON).is_visible():
            self.page.locator(self.PERMISSION_ACCEPT_BUTTON).click()
            self.page.wait_for_timeout(10000)
        else:
            self.page.locator(self.YES_BUTTON).click()
            self.page.wait_for_timeout(10000)


        self.page.wait_for_load_state("networkidle")


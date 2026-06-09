import pytest
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# conftest.py content (integrated for single file output)

def pytest_addoption(parser):
    parser.addoption("--browser", action="store", default="chrome", help="Type of browser to use (chrome, firefox, edge)")
    parser.addoption("--baseurl", action="store", default="http://localhost:5173", help="Base URL for the application")

@pytest.fixture(scope="session")
def browser_type(request):
    return request.config.getoption("--browser")

@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--baseurl")

@pytest.fixture(scope="class")
def setup_driver(request, browser_type, base_url):
    driver = None
    if browser_type == "chrome":
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
    elif browser_type == "firefox":
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service)
    elif browser_type == "edge":
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service)
    else:
        raise ValueError(f"Unsupported browser: {browser_type}")

    driver.maximize_window()
    request.cls.driver = driver
    request.cls.base_url = base_url
    yield driver
    driver.quit()

# pages/login_page.py content (integrated for single file output)

class LoginPage:
    # Locators
    USERNAME_FIELD = (By.CSS_SELECTOR, "input[placeholder='Enter username']")
    PASSWORD_FIELD = (By.CSS_SELECTOR, "input[placeholder='Enter password']")
    LOGIN_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
    CREDENTIALS_HINT = (By.CSS_SELECTOR, "p.text-yellow-500")
    # Assuming an error message will appear containing "invalid credentials"
    ERROR_MESSAGE = (By.XPATH, "//*[contains(text(), 'invalid credentials')]") 
    
    DASHBOARD_URL_PATH = "/dashboard"
    LOGIN_URL_PATH = "/"

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(self.driver, 10)

    def go_to_login_page(self):
        self.driver.get(self.base_url + self.LOGIN_URL_PATH)
        self.wait.until(EC.visibility_of_element_located(self.USERNAME_FIELD))

    def enter_username(self, username):
        self.wait.until(EC.visibility_of_element_located(self.USERNAME_FIELD)).send_keys(username)

    def enter_password(self, password):
        self.wait.until(EC.visibility_of_element_located(self.PASSWORD_FIELD)).send_keys(password)

    def click_login_button(self):
        self.wait.until(EC.element_to_be_clickable(self.LOGIN_BUTTON)).click()

    def get_current_url(self):
        return self.driver.current_url

    def is_error_message_displayed(self):
        try:
            self.wait.until(EC.visibility_of_element_located(self.ERROR_MESSAGE))
            return True
        except TimeoutException:
            return False

    def get_error_message_text(self):
        try:
            return self.wait.until(EC.visibility_of_element_located(self.ERROR_MESSAGE)).text
        except TimeoutException:
            return None

    def is_credentials_hint_displayed(self):
        try:
            self.wait.until(EC.visibility_of_element_located(self.CREDENTIALS_HINT))
            return True
        except TimeoutException:
            return False

    def get_password_field_type(self):
        return self.wait.until(EC.visibility_of_element_located(self.PASSWORD_FIELD)).get_attribute("type")

    def get_username_field_value(self):
        return self.wait.until(EC.visibility_of_element_located(self.USERNAME_FIELD)).get_attribute("value")

    def get_password_field_value(self):
        return self.wait.until(EC.visibility_of_element_located(self.PASSWORD_FIELD)).get_attribute("value")
    
    def get_username_field_autocomplete_attribute(self):
        return self.wait.until(EC.visibility_of_element_located(self.USERNAME_FIELD)).get_attribute("autocomplete")

    def get_password_field_autocomplete_attribute(self):
        return self.wait.until(EC.visibility_of_element_located(self.PASSWORD_FIELD)).get_attribute("autocomplete")

    def is_username_field_present(self):
        try:
            self.driver.find_element(*self.USERNAME_FIELD)
            return True
        except NoSuchElementException:
            return False

    def is_password_field_present(self):
        try:
            self.driver.find_element(*self.PASSWORD_FIELD)
            return True
        except NoSuchElementException:
            return False

    def is_login_button_present(self):
        try:
            self.driver.find_element(*self.LOGIN_BUTTON)
            return True
        except NoSuchElementException:
            return False

    def wait_for_url_change(self, expected_path, timeout=10):
        self.wait.until(EC.url_contains(expected_path))

    def wait_for_login_page(self, timeout=10):
        self.wait.until(EC.url_contains(self.LOGIN_URL_PATH))
        self.wait.until(EC.visibility_of_element_located(self.USERNAME_FIELD))


# tests/test_login.py content (integrated for single file output)

@pytest.mark.usefixtures("setup_driver")
class TestLogin:
    driver = None
    base_url = None

    @pytest.fixture(autouse=True)
    def setup_pages(self):
        self.login_page = LoginPage(self.driver, self.base_url)

    # Test Scenario ID: LOGIN-POS-001
    def test_successful_login_with_valid_admin_credentials(self):
        """Verify successful login with valid 'admin' credentials."""
        self.login_page.go_to_login_page()
        self.login_page.enter_username("admin")
        self.login_page.enter_password("admin123")
        self.login_page.click_login_button()
        
        # Expected Result: User is successfully redirected to the Dashboard view (`/dashboard`)
        self.login_page.wait_for_url_change(self.login_page.DASHBOARD_URL_PATH)
        assert self.login_page.get_current_url().endswith(self.login_page.DASHBOARD_URL_PATH)

    # Test Scenario ID: LOGIN-NEG-001
    def test_failed_login_with_invalid_username(self):
        """Verify failed login with an invalid username."""
        self.login_page.go_to_login_page()
        self.login_page.enter_username("invaliduser")
        self.login_page.enter_password("admin123")
        self.login_page.click_login_button()

        # Expected Result: User remains on the Login page & "invalid credentials" message
        assert self.login_page.get_current_url().endswith(self.login_page.LOGIN_URL_PATH)
        assert self.login_page.is_error_message_displayed()
        assert "invalid credentials" in self.login_page.get_error_message_text().lower()

    # Test Scenario ID: LOGIN-NEG-002
    def test_failed_login_with_invalid_password(self):
        """Verify failed login with an invalid password."""
        self.login_page.go_to_login_page()
        self.login_page.enter_username("admin")
        self.login_page.enter_password("wrongpass")
        self.login_page.click_login_button()

        # Expected Result: User remains on the Login page & "invalid credentials" message
        assert self.login_page.get_current_url().endswith(self.login_page.LOGIN_URL_PATH)
        assert self.login_page.is_error_message_displayed()
        assert "invalid credentials" in self.login_page.get_error_message_text().lower()

    # Test Scenario ID: LOGIN-NEG-003
    def test_failed_login_with_both_invalid_username_and_password(self):
        """Verify failed login with both invalid username and password."""
        self.login_page.go_to_login_page()
        self.login_page.enter_username("invaliduser")
        self.login_page.enter_password("wrongpass")
        self.login_page.click_login_button()

        # Expected Result: User remains on the Login page & "invalid credentials" message
        assert self.login_page.get_current_url().endswith(self.login_page.LOGIN_URL_PATH)
        assert self.login_page.is_error_message_displayed()
        assert "invalid credentials" in self.login_page.get_error_message_text().lower()

    # Test Scenario ID: LOGIN-UI-001 (Bug B11)
    def test_password_visibility_in_password_field(self):
        """Verify password visibility in the password field."""
        self.login_page.go_to_login_page()
        test_password = "testpassword123"
        self.login_page.enter_password(test_password)

        # Expected Result: BUG: The entered password text is visible in plaintext (not masked)
        assert self.login_page.get_password_field_type() == "text"
        assert self.login_page.get_password_field_value() == test_password

    # Test Scenario ID: LOGIN-UI-002 (Bug B12)
    def test_presence_of_credentials_hint_on_login_form(self):
        """Verify the presence of credentials hint on the login form."""
        self.login_page.go_to_login_page()

        # Expected Result: BUG: A credentials hint (e.g., "admin / admin123") is displayed
        assert self.login_page.is_credentials_hint_displayed()
        # Optionally, verify the text content
        credentials_hint_element = self.driver.find_element(*self.login_page.CREDENTIALS_HINT)
        assert "Demo: admin / admin123" in credentials_hint_element.text

    # Test Scenario ID: LOGIN-NEG-004 (Bug B13)
    def test_behavior_when_submitting_empty_login_form(self):
        """Verify behavior when submitting an empty login form (no username, no password)."""
        self.login_page.go_to_login_page()
        # Fields are initially empty, just click login
        self.login_page.click_login_button()

        # Expected Result: BUG: System attempts to authenticate, user remains on Login page, "invalid credentials" message
        assert self.login_page.get_current_url().endswith(self.login_page.LOGIN_URL_PATH)
        assert self.login_page.is_error_message_displayed()
        assert "invalid credentials" in self.login_page.get_error_message_text().lower()

    # Test Scenario ID: LOGIN-NEG-005 (Bug B13)
    def test_behavior_when_submitting_with_only_username_provided(self):
        """Verify behavior when submitting with only username provided (empty password)."""
        self.login_page.go_to_login_page()
        self.login_page.enter_username("admin")
        # Password field is left empty
        self.login_page.click_login_button()

        # Expected Result: BUG: System attempts to authenticate, user remains on Login page, "invalid credentials" message
        assert self.login_page.get_current_url().endswith(self.login_page.LOGIN_URL_PATH)
        assert self.login_page.is_error_message_displayed()
        assert "invalid credentials" in self.login_page.get_error_message_text().lower()

    # Test Scenario ID: LOGIN-NEG-006 (Bug B13)
    def test_behavior_when_submitting_with_only_password_provided(self):
        """Verify behavior when submitting with only password provided (empty username)."""
        self.login_page.go_to_login_page()
        # Username field is left empty
        self.login_page.enter_password("admin123")
        self.login_page.click_login_button()

        # Expected Result: BUG: System attempts to authenticate, user remains on Login page, "invalid credentials" message
        assert self.login_page.get_current_url().endswith(self.login_page.LOGIN_URL_PATH)
        assert self.login_page.is_error_message_displayed()
        assert "invalid credentials" in self.login_page.get_error_message_text().lower()

    # Test Scenario ID: LOGIN-UI-003 (Bug B14)
    def test_browser_autocomplete_functionality_for_login_fields(self):
        """Verify browser autocomplete functionality for login fields."""
        self.login_page.go_to_login_page()

        # Expected Result: BUG: The browser offers to autocomplete or suggests previously entered credentials
        # This means 'autocomplete="off"' is NOT set.
        # We check if the attribute is either missing or not explicitly 'off'.
        username_autocomplete = self.login_page.get_username_field_autocomplete_attribute()
        password_autocomplete = self.login_page.get_password_field_autocomplete_attribute()

        # The bug states 'autocomplete='off' is not set'. So, we assert it's not 'off'.
        # If the attribute is entirely absent, get_attribute returns None.
        assert username_autocomplete != "off"
        assert password_autocomplete != "off"

    # Test Scenario ID: LOGIN-SESSION-001
    def test_user_session_is_maintained_after_successful_login_and_navigation(self):
        """Verify user session is maintained after successful login and navigation."""
        # Precondition: User has successfully logged in
        self.login_page.go_to_login_page()
        self.login_page.enter_username("admin")
        self.login_page.enter_password("admin123")
        self.login_page.click_login_button()
        self.login_page.wait_for_url_change(self.login_page.DASHBOARD_URL_PATH)
        assert self.login_page.get_current_url().endswith(self.login_page.DASHBOARD_URL_PATH)

        # Step 1: From the Dashboard, navigate to another available module (simulated by refreshing the page)
        # A refresh is a good way to check if session state persists without explicit navigation links.
        self.driver.refresh()
        
        # Expected Result: The user remains logged in and can access all authenticated features
        # (i.e., still on the dashboard, not redirected to login)
        self.login_page.wait_for_url_change(self.login_page.DASHBOARD_URL_PATH)
        assert self.login_page.get_current_url().endswith(self.login_page.DASHBOARD_URL_PATH)
        
        # Verify that login page elements are not visible, indicating session maintained.
        try:
            WebDriverWait(self.driver, 5).until(EC.invisibility_of_element_located(self.login_page.USERNAME_FIELD))
            # If the element becomes invisible, it means the login page is not present.
            # This assertion will pass if the login page elements are indeed invisible.
            # If the element is still visible, a TimeoutException will occur, and the test will fail.
        except TimeoutException:
            pytest.fail("Login page elements are still visible after refresh, indicating session loss.")

    # Test Scenario ID: LOGIN-UI-004
    def test_presence_and_labels_of_login_form_elements(self):
        """Verify the presence and labels of username and password fields and the login button."""
        self.login_page.go_to_login_page()

        # Expected Result: Username field, Password field, Login button are present and visible.
        assert self.login_page.is_username_field_present()
        assert self.login_page.is_password_field_present()
        assert self.login_page.is_login_button_present()

        # Verify labels (using XPATH for text content of labels)
        username_label = self.driver.find_element(By.XPATH, "//label[text()='Username']")
        password_label = self.driver.find_element(By.XPATH, "//label[text()='Password']")
        login_button_text = self.driver.find_element(By.XPATH, "//button[text()='Login']")

        assert username_label.is_displayed()
        assert password_label.is_displayed()
        assert login_button_text.is_displayed()

    # Test Scenario ID: LOGIN-UI-005
    def test_initial_state_of_login_form_fields(self):
        """Verify the initial state of the login form fields."""
        self.login_page.go_to_login_page()

        # Expected Result: Both Username and Password fields are empty. No error messages.
        assert self.login_page.get_username_field_value() == ""
        assert self.login_page.get_password_field_value() == ""
        assert not self.login_page.is_error_message_displayed()

# This block ensures pytest can discover and run tests, and custom options are registered.
if __name__ == "__main__":
    # Add the current directory to sys.path to allow pytest to find modules
    sys.path.insert(0, '.') 
    pytest.main([__file__], plugins=[sys.modules[__name__]])
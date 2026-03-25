"""
Step definitions for Recommendation Service BDD tests.

All steps are generic and reusable across scenarios (Create, Read, Update,
Delete, List, Query, Action).
"""

from behave import given, when, then
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Mapping from human-readable field labels to HTML element IDs
FIELD_ID_MAP = {
    "ID": "recommendation_id",
    "Product ID": "recommendation_product_id",
    "Recommended Product ID": "recommendation_recommended_product_id",
    "Recommendation Type": "recommendation_type",
    "Score": "recommendation_score",
}

# Mapping from human-readable button labels to HTML element IDs
BUTTON_ID_MAP = {
    "Create": "create-btn",
    "Retrieve": "retrieve-btn",
    "Update": "update-btn",
    "Delete": "delete-btn",
    "List": "list-btn",
    "Clear": "clear-btn",
}


@given('I am on the "Home Page"')
def step_go_to_home_page(context):
    """Navigate to the home page."""
    context.driver.get(context.base_url)
    WebDriverWait(context.driver, 10).until(
        EC.presence_of_element_located((By.ID, "create-btn"))
    )


@when('I set the "{field}" to "{value}"')
def step_set_field(context, field, value):
    """Set an input field to a value (for text/number inputs)."""
    element_id = FIELD_ID_MAP.get(field, field)
    element = context.driver.find_element(By.ID, element_id)
    element.clear()
    element.send_keys(value)


@when('I select "{value}" in the "{field}" dropdown')
def step_select_dropdown(context, value, field):
    """Select a value from a dropdown (select element)."""
    element_id = FIELD_ID_MAP.get(field, field)
    element = context.driver.find_element(By.ID, element_id)
    Select(element).select_by_value(value)


@when('I press the "{button}" button')
def step_press_button(context, button):
    """Click a button by its label."""
    element_id = BUTTON_ID_MAP.get(button, button)
    element = context.driver.find_element(By.ID, element_id)
    element.click()


@then('I should see the message "{message}"')
def step_check_flash_message(context, message):
    """Verify the flash message contains the expected text."""
    flash = WebDriverWait(context.driver, 10).until(
        EC.visibility_of_element_located((By.ID, "flash_message"))
    )
    assert message in flash.text, (
        f"Expected '{message}' in flash message, got '{flash.text}'"
    )


@then('I should see "{value}" in the "{field}" field')
def step_check_field_value(context, value, field):
    """Verify an input field contains the expected value."""
    element_id = FIELD_ID_MAP.get(field, field)
    element = context.driver.find_element(By.ID, element_id)
    actual = element.get_attribute("value")
    assert value == actual, (
        f"Expected '{value}' in '{field}', got '{actual}'"
    )


@then('I should see "{value}" in the "{field}" dropdown')
def step_check_dropdown_value(context, value, field):
    """Verify a dropdown has the expected value selected."""
    element_id = FIELD_ID_MAP.get(field, field)
    element = context.driver.find_element(By.ID, element_id)
    actual = Select(element).first_selected_option.get_attribute("value")
    assert value == actual, (
        f"Expected '{value}' in '{field}' dropdown, got '{actual}'"
    )


@then('I should see a value in the "{field}" field')
def step_check_field_has_value(context, field):
    """Verify an input field is not empty (has some value)."""
    element_id = FIELD_ID_MAP.get(field, field)
    element = context.driver.find_element(By.ID, element_id)
    actual = element.get_attribute("value")
    assert actual and actual.strip(), (
        f"Expected a non-empty value in '{field}', got '{actual}'"
    )


@when('I copy the "{field}" field')
def step_copy_field(context, field):
    """Copy the value of a field to the context clipboard."""
    element_id = FIELD_ID_MAP.get(field, field)
    element = context.driver.find_element(By.ID, element_id)
    context.clipboard = element.get_attribute("value")


@when('I paste the "{field}" field')
def step_paste_field(context, field):
    """Paste the clipboard value into a field."""
    element_id = FIELD_ID_MAP.get(field, field)
    element = context.driver.find_element(By.ID, element_id)
    element.clear()
    element.send_keys(context.clipboard)

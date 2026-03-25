Feature: Recommendation Service
    As an eCommerce manager
    I need a web user interface
    So that I can manage product recommendations

Background:
    Given I am on the "Home Page"

Scenario: Create a Recommendation
    When I set the "Product ID" to "1"
    And I set the "Recommended Product ID" to "2"
    And I select "cross_sell" in the "Recommendation Type" dropdown
    And I set the "Score" to "0.95"
    And I press the "Create" button
    Then I should see the message "Success"
    And I should see "1" in the "Product ID" field
    And I should see "2" in the "Recommended Product ID" field
    And I should see "cross_sell" in the "Recommendation Type" dropdown
    And I should see "0.95" in the "Score" field
    And I should see a value in the "ID" field

Scenario: Read a Recommendation
    When I set the "Product ID" to "1"
    And I set the "Recommended Product ID" to "2"
    And I select "cross_sell" in the "Recommendation Type" dropdown
    And I set the "Score" to "0.95"
    And I press the "Create" button
    Then I should see the message "Success"
    When I copy the "ID" field
    And I press the "Clear" button
    And I paste the "ID" field
    And I press the "Retrieve" button
    Then I should see the message "Success"
    And I should see "1" in the "Product ID" field
    And I should see "2" in the "Recommended Product ID" field
    And I should see "cross_sell" in the "Recommendation Type" dropdown
    And I should see "0.95" in the "Score" field

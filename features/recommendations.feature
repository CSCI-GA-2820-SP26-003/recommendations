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

Scenario: Update a Recommendation
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
    When I set the "Product ID" to "10"
    And I set the "Recommended Product ID" to "20"
    And I select "up_sell" in the "Recommendation Type" dropdown
    And I set the "Score" to "0.5"
    And I press the "Update" button
    Then I should see the message "Success"
    When I copy the "ID" field
    And I press the "Clear" button
    And I paste the "ID" field
    And I press the "Retrieve" button
    Then I should see the message "Success"
    And I should see "10" in the "Product ID" field
    And I should see "20" in the "Recommended Product ID" field
    And I should see "up_sell" in the "Recommendation Type" dropdown
    And I should see "0.5" in the "Score" field

Scenario: Delete a Recommendation
    When I set the "Product ID" to "1"
    And I set the "Recommended Product ID" to "2"
    And I select "cross_sell" in the "Recommendation Type" dropdown
    And I set the "Score" to "0.95"
    And I press the "Create" button
    Then I should see the message "Success"
    When I copy the "ID" field
    And I press the "Clear" button
    And I paste the "ID" field
    And I press the "Delete" button
    Then I should see the message "Recommendation has been Deleted!"
    When I paste the "ID" field
    And I press the "Retrieve" button
    Then I should see the message "Recommendation not found"

Scenario: List all Recommendations
    When I set the "Product ID" to "1"
    And I set the "Recommended Product ID" to "2"
    And I select "cross_sell" in the "Recommendation Type" dropdown
    And I set the "Score" to "0.95"
    And I press the "Create" button
    Then I should see the message "Success"
    When I press the "Clear" button
    And I press the "List" button
    Then I should see the message "Success"
    And I should see "1" recommendation in the results

Scenario: Query Recommendations by Attribute
    When I set the "Product ID" to "1"
    And I set the "Recommended Product ID" to "2"
    And I select "cross_sell" in the "Recommendation Type" dropdown
    And I set the "Score" to "0.95"
    And I press the "Create" button
    Then I should see the message "Success"
    When I press the "Clear" button
    And I set the "Product ID" to "10"
    And I set the "Recommended Product ID" to "20"
    And I select "up_sell" in the "Recommendation Type" dropdown
    And I set the "Score" to "0.50"
    And I press the "Create" button
    Then I should see the message "Success"
    When I press the "Clear" button
    And I set the "Search Product ID" to "10"
    And I select "up_sell" in the "Search Recommendation Type" dropdown
    And I press the "Search" button
    Then I should see the message "Success"
    And I should see "1" recommendation in the results

Scenario: Activate and Deactivate a Recommendation
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
    And I should see "true" in the "Active" field
    When I press the "Deactivate" button
    Then I should see the message "Recommendation has been deactivated!"
    And I should see "false" in the "Active" field
    When I press the "Activate" button
    Then I should see the message "Recommendation has been activated!"
    And I should see "true" in the "Active" field

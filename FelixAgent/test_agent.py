"""Test script for the Send Money Agent."""

from .send_money_agent import collect_transfer_details, send_money
from google.adk.tools.tool_context import ToolContext
import json


class MockToolContext:
    """Mock ToolContext for testing."""
    def __init__(self):
        self.state = {}


def test_complete_flow():
    """Test a complete flow where all information is provided."""
    print("=" * 60)
    print("Test 1: Complete Information Flow")
    print("=" * 60)
    
    tool_context = MockToolContext()
    
    # Test with supported country and currency
    user_input = "I want to send $500 USD to John Smith AC123456 in Colombia via Bank Transfer"
    print(f"\nUser: {user_input}")
    response = collect_transfer_details(tool_context, user_input)
    print(f"Agent: {response}")
    
    # Check if all information was collected by checking the state directly
    state = tool_context.state
    assert state.get('amount') == 500.0, f"Amount should be 500, got {state.get('amount')}"
    assert state.get('currency') == 'USD', f"Currency should be USD, got {state.get('currency')}"
    assert state.get('beneficiary_account') is not None, "Beneficiary account should be set"
    assert state.get('country') == 'COLOMBIA', f"Country should be COLOMBIA, got {state.get('country')}"
    assert state.get('delivery_method') == 'Bank Transfer', f"Delivery method should be Bank Transfer, got {state.get('delivery_method')}"
    print("\n✓ Test passed: All information collected")
    print("\nState:", json.dumps(state, indent=2, default=str))


def test_step_by_step():
    """Test step-by-step information collection."""
    print("\n" + "=" * 60)
    print("Test 2: Step-by-Step Collection")
    print("=" * 60)
    
    tool_context = MockToolContext()
    
    steps = [
        ("$200", "Should collect amount"),
        ("USD", "Should collect currency"),
        ("Mary Johnson", "Should collect beneficiary name"),
        ("AC987654", "Should collect account number"),
        ("Mexico", "Should collect country"),
        ("Mobile Wallet", "Should collect delivery method")
    ]
    
    for step_input, description in steps:
        print(f"\nUser: {step_input} ({description})")
        response = collect_transfer_details(tool_context, step_input)
        print(f"Agent: {response}")
    
    # Verify all information was collected by checking the state directly
    state = tool_context.state
    assert state.get('amount') == 200.0, "Amount should be 200"
    assert state.get('currency') == 'USD', "Currency should be USD"
    assert state.get('beneficiary_name') == 'Mary Johnson', "Beneficiary name should be Mary Johnson"
    assert state.get('beneficiary_account') is not None, "Account number should be set"
    assert state.get('country') == 'MEXICO', "Country should be MEXICO"
    assert state.get('delivery_method') == 'Mobile Wallet', "Delivery method should be Mobile Wallet"
    print("\n✓ Test passed: Step-by-step collection works")
    print("\nState:", json.dumps(state, indent=2, default=str))


def test_correction():
    """Test correction handling."""
    print("\n" + "=" * 60)
    print("Test 3: Correction Handling")
    print("=" * 60)
    
    tool_context = MockToolContext()
    
    # Provide initial information
    print("\nUser: Send $100 to Bob AC123456")
    response = collect_transfer_details(tool_context, "Send $100 to Bob AC123456")
    print(f"Agent: {response}")
    
    # Make a correction
    print("\nUser: Actually, change the amount to $300")
    response = collect_transfer_details(tool_context, "Actually, change the amount to $300")
    print(f"Agent: {response}")
    
    # Verify correction by checking the state directly
    state = tool_context.state
    assert state.get('amount') == 300.0, f"Amount should be corrected to 300, got {state.get('amount')}"
    assert state.get('beneficiary_name') == 'Bob', "Beneficiary name should still be Bob"
    print("\n✓ Test passed: Correction handled correctly")


def test_name_with_account_number():
    """Test that name followed by number is recognized as account number."""
    print("\n" + "=" * 60)
    print("Test 4: Name with Account Number")
    print("=" * 60)
    
    tool_context = MockToolContext()
    
    # Test name followed by number (like "DANIELA VARELA 203933773")
    print("\nUser: Daniela Varela 203933773")
    response = collect_transfer_details(tool_context, "Daniela Varela 203933773")
    print(f"Agent: {response}")
    
    state = tool_context.state
    assert state.get('beneficiary_name') == 'Daniela Varela', f"Name should be 'Daniela Varela', got {state.get('beneficiary_name')}"
    assert state.get('beneficiary_account') is not None, "Account number should be extracted from the number"
    print("\n✓ Test passed: Name and account number extracted correctly")


def test_state_persistence():
    """Test that state persists across multiple turns."""
    print("\n" + "=" * 60)
    print("Test 5: State Persistence")
    print("=" * 60)
    
    tool_context = MockToolContext()
    
    # First turn
    print("\nUser: I want to send $500")
    response1 = collect_transfer_details(tool_context, "I want to send $500")
    print(f"Agent: {response1}")
    
    # Second turn - should remember amount
    print("\nUser: USD")
    response2 = collect_transfer_details(tool_context, "USD")
    print(f"Agent: {response2}")
    
    # Verify state directly
    state = tool_context.state
    assert state.get('amount') == 500.0, f"Amount should be remembered as 500, got {state.get('amount')}"
    assert state.get('currency') == "USD", f"Currency should be set to USD, got {state.get('currency')}"
    print("\n✓ Test passed: State persists across turns")


def test_send_money():
    """Test the send_money function with complete information."""
    print("\n" + "=" * 60)
    print("Test 6: Send Money")
    print("=" * 60)
    
    tool_context = MockToolContext()
    
    # First collect all information
    print("\nCollecting information...")
    collect_transfer_details(tool_context, "$100 USD to John Smith AC123456 in Colombia via Card")
    
    # Verify all info is collected by checking the state directly
    state = tool_context.state
    assert state.get('amount') is not None, "Amount should be set"
    assert state.get('currency') is not None, "Currency should be set"
    assert state.get('beneficiary_account') is not None, "Account should be set"
    assert state.get('country') is not None, "Country should be set"
    assert state.get('delivery_method') is not None, "Delivery method should be set"
    
    # Now send the money
    print("\nUser: Yes, send it")
    response = send_money(tool_context)
    print(f"Agent: {response}")
    
    # Verify response contains transfer confirmation
    assert "successful" in response.lower() or "transaction" in response.lower() or "sent" in response.lower(), "Response should indicate successful transfer"
    print("\n✓ Test passed: Send money works correctly")


def test_supported_countries():
    """Test that all supported countries work correctly."""
    print("\n" + "=" * 60)
    print("Test 7: Supported Countries")
    print("=" * 60)
    
    countries = ['MEXICO', 'HONDURAS', 'COLOMBIA', 'NICARAGUA', 'GUATEMALA', 'EL SALVADOR', 'REPUBLICA DOMINICANA']
    
    for country in countries:
        tool_context = MockToolContext()
        print(f"\nTesting country: {country}")
        response = collect_transfer_details(tool_context, f"Send $100 to John AC123456 in {country}")
        state = tool_context.state
        assert state.get('country') == country, f"Country should be {country}, got {state.get('country')}"
        print(f"  ✓ {country} recognized correctly")
    
    print("\n✓ Test passed: All supported countries work")


if __name__ == "__main__":
    try:
        test_complete_flow()
        test_step_by_step()
        test_correction()
        test_name_with_account_number()
        test_state_persistence()
        test_send_money()
        test_supported_countries()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()

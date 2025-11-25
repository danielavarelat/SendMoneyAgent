"""Send Money Agent using Google ADK Framework (ADK 1.18)."""

from typing import Any, Dict, Optional
from google.adk.tools.tool_context import ToolContext

from .send_money_state import SendMoneyState
from .utils import (
    extract_amount, extract_currency, extract_country,
    extract_beneficiary_name, extract_account_number, extract_delivery_method,
    get_expected_formats, COUNTRY_CURRENCY_MAP,
    validate_country_value, validate_currency_value, validate_delivery_method_value,
    detect_correction
)


def _get_state_from_context(tool_context: ToolContext) -> Dict[str, Any]:
    """Get state from ADK's ToolContext (session state).
    
    ADK's ToolContext.state is a dict-like State object that supports
    dict operations. We use it directly without conversion.
    """
    if tool_context.state is None:
        # Initialize empty state if None
        tool_context.state = {}
    # Return the state object directly - it's dict-like and supports all dict operations
    # The ADK State object works with .get(), .update(), item access, etc.
    return tool_context.state


def _update_state_in_context(tool_context: ToolContext, state_dict: Dict[str, Any]) -> None:
    """Update state in ADK's ToolContext by updating the dictionary in place.
    
    ADK's ToolContext.state is a dict-like State object that supports .update().
    We update it in place so the UI can see the changes.
    """
    if tool_context.state is None:
        # Initialize empty state if None
        tool_context.state = {}
    
    # Update the state object in place - ADK's State object supports .update()
    # Keep all fields (including None) so the UI can see the full state structure
    tool_context.state.update(state_dict)


def _state_to_send_money_state(state_dict: Dict[str, Any]) -> SendMoneyState:
    """Convert dictionary state to SendMoneyState object."""
    return SendMoneyState(
        amount=state_dict.get('amount'),
        currency=state_dict.get('currency'),
        beneficiary_account=state_dict.get('beneficiary_account'),
        beneficiary_name=state_dict.get('beneficiary_name'),
        country=state_dict.get('country'),
        delivery_method=state_dict.get('delivery_method'),
    )


def _send_money_state_to_dict(state: SendMoneyState) -> Dict[str, Any]:
    """Convert SendMoneyState object to dictionary for storage.
    
    Always includes all fields (even if None) so the UI can display the full state structure.
    """
    return {
        'amount': state.amount,
        'currency': state.currency,
        'beneficiary_account': state.beneficiary_account,
        'beneficiary_name': state.beneficiary_name,
        'country': state.country,
        'delivery_method': state.delivery_method,
    }


def collect_transfer_details(tool_context: ToolContext, user_input: str) -> str:
    """
    Simplified and stable version of transfer detail collection.
    
    Still meets all requirements:
    - Slot filling (amount, currency, beneficiary, country, delivery method)
    - Corrections ("change amount to 200")
    - Beneficiary lookup via account or name
    - Ambiguity handling via separate tool
    - Natural step-by-step prompts
    """
    # Load state
    state_dict = _get_state_from_context(tool_context)
    state = _state_to_send_money_state(state_dict)
    text = user_input.strip().lower()

    # --- 1) CORRECTIONS (simple and explicit) ---
    correction_field, correction_value = detect_correction(user_input)
    if correction_field:
        # Try to re-extract the new value using our extractors
        field_extractors = {
            "amount": extract_amount,
            "currency": extract_currency,
            "country": extract_country,
            "beneficiary_name": extract_beneficiary_name,
            "beneficiary_account": extract_account_number,
            "delivery_method": extract_delivery_method
        }
        extractor = field_extractors.get(correction_field)
        if extractor:
            new_value = extractor(correction_value or user_input)
            if new_value:
                state.update_field(correction_field, new_value)
                _update_state_in_context(tool_context, _send_money_state_to_dict(state))
                return f"Got it — I updated the {correction_field.replace('_',' ')} to {new_value}. " + _next_missing_question(state)
        return f"I understand you want to change the {correction_field}, but I couldn't extract the new value."

    # --- 2) EXTRACTION (context-aware, based on what's missing) ---
    extracted = {}
    
    # Determine what field is most likely being provided based on what's missing
    # Priority: if a field is missing, prioritize extraction for that field
    missing_fields = []
    if state.amount is None:
        missing_fields.append("amount")
    if state.currency is None:
        missing_fields.append("currency")
    if state.beneficiary_account is None:
        missing_fields.append("beneficiary_account")
    if state.country is None:
        missing_fields.append("country")
    if state.delivery_method is None:
        missing_fields.append("delivery_method")

    # Amount
    amt = extract_amount(user_input)
    if amt and state.amount != amt:
        extracted["amount"] = amt

    # Currency - prioritize if currency is missing
    cur = extract_currency(user_input)
    if cur and state.currency != cur:
        # Validate currency
        is_valid, error_msg = validate_currency_value(cur)
        if not is_valid:
            formats = get_expected_formats()
            # Save state before returning error
            _update_state_in_context(tool_context, _send_money_state_to_dict(state))
            return f"I'm sorry, but {error_msg}. Please use the expected format: {formats['currency']}. What currency would you like to use?"
        extracted["currency"] = cur

    # Country - extract if found
    # extract_country only matches actual country names, not currency codes, so it's safe to extract
    # even when currency is also present in the input
    ctry = extract_country(user_input)
    if ctry and state.country != ctry:
        # Validate country
        is_valid, error_msg = validate_country_value(ctry)
        if not is_valid:
            # Save state before returning error
            _update_state_in_context(tool_context, _send_money_state_to_dict(state))
            return f"{error_msg} Which country should the money be sent to?"
        extracted["country"] = ctry
    elif ctry is None and state.country is None and cur is None:
        # Only check for country-like input if:
        # 1. No country was extracted
        # 2. No currency was extracted in this input (context-aware)
        # 3. Country is still missing
        # 4. Currency is NOT currently the missing field (if currency is missing, prioritize currency extraction)
        # 5. Check if a beneficiary name was extracted - if so, don't validate as country
        name_check = extract_beneficiary_name(user_input)
        if "currency" not in missing_fields or state.currency is not None:
            user_input_upper = user_input.strip().upper()
            # Only validate as country if:
            # - It's a single word (most countries are single words, except "EL SALVADOR" and "REPUBLICA DOMINICANA")
            # - No beneficiary name was extracted (if name was extracted, it's clearly not a country)
            # - Not a currency code
            # - Not already in our country map
            if (user_input_upper and 
                name_check is None and  # No name was extracted - if name was extracted, don't validate as country
                user_input_upper not in COUNTRY_CURRENCY_MAP and
                user_input_upper not in ['USD', 'MXN', 'HNL', 'DOP', 'NIO', 'COP', 'GTQ'] and  # Not a currency code
                not any(char.isdigit() for char in user_input_upper) and
                len(user_input_upper.split()) == 1):  # Only single words (to avoid matching names like "Mary Johnson")
                # Try to validate it - this will give us a proper error message
                is_valid, error_msg = validate_country_value(user_input.strip())
                if not is_valid:
                    # Save state before returning error
                    _update_state_in_context(tool_context, _send_money_state_to_dict(state))
                    return f"{error_msg} Which country should the money be sent to?"

    # Account number - extract AFTER country to avoid false matches
    # Only extract if we haven't already extracted a country that might be confused with an account
    acct = extract_account_number(user_input)
    if acct and state.beneficiary_account != acct:
        # Double-check: if the extracted account looks like a country name, skip it
        if acct.upper() not in COUNTRY_CURRENCY_MAP:
            extracted["beneficiary_account"] = acct

    # Beneficiary name
    name = extract_beneficiary_name(user_input)
    if name and state.beneficiary_name != name:
        # Validate that the extracted name is not a common phrase or invalid
        name_lower = name.lower()
        invalid_name_phrases = [
            'send money', 'send money to', 'send to', 'money to', 'want to send',
            'help me send', 'i want to', 'would like to', 'need to send', 'to send'
        ]
        # Reject if the name contains invalid phrases
        if any(phrase in name_lower for phrase in invalid_name_phrases):
            # Don't extract this as a name - it's likely a phrase, not a real name
            pass
        else:
            extracted["beneficiary_name"] = name

    # Delivery method
    dm = extract_delivery_method(user_input)
    if dm and state.delivery_method != dm:
        # Validate delivery method
        is_valid, error_msg = validate_delivery_method_value(dm)
        if not is_valid:
            formats = get_expected_formats()
            # Save state before returning error
            _update_state_in_context(tool_context, _send_money_state_to_dict(state))
            return f"I'm sorry, but {error_msg}. Please use one of the supported methods: {formats['delivery_method']}. How would you like the money to be delivered?"
        extracted["delivery_method"] = dm

    # --- 3) If nothing was extracted ---
    if not extracted:
        # Show what we have and ask for the next missing field
        collected_info = _format_collected_info(state)
        next_question = _next_missing_question(state)
        if collected_info:
            return f"{collected_info}\n\n{next_question}"
        else:
            return next_question

    # --- 4) Apply extracted fields ---
    for field, value in extracted.items():
        state.update_field(field, value)

    _update_state_in_context(tool_context, _send_money_state_to_dict(state))

    # --- 5) If complete → summary ---
    if state.is_complete():
        summary = state.get_summary()
        beneficiary_display = f"{summary['beneficiary_name']} (Acct {summary['beneficiary_account']})" if summary.get('beneficiary_name') else f"Acct {summary['beneficiary_account']}"
        return (
            "Great, I have everything!\n\n"
            f"**Amount:** {summary['amount']} {summary['currency']}\n"
            f"**Beneficiary:** {beneficiary_display}\n"
            f"**Country:** {summary['country']}\n"
            f"**Delivery Method:** {summary['delivery_method']}\n\n"
            "Would you like to proceed with the transfer?"
        )

    # --- 6) Otherwise → ALWAYS show collected info and ask next question ---
    # Format collected info - state object has the latest values after update
    collected_info = _format_collected_info(state)
    next_question = _next_missing_question(state)
    
    # ALWAYS show collected info if we have any collected fields, then ask next question
    # This ensures users always see what information has been collected
    if collected_info:
        return f"{collected_info}\n\n{next_question}"
    # If no collected info, just return the next question
    return next_question


def _format_collected_info(state: SendMoneyState) -> str:
    """Format the currently collected information as a nice list."""
    collected = []
    
    # Amount
    if state.amount is not None and state.currency is not None:
        collected.append(f"**Amount:** {state.amount} {state.currency}")
    elif state.amount is not None:
        collected.append(f"**Amount:** {state.amount}")
    
    # Beneficiary - check for both name and account (handle None and empty strings)
    # Use truthiness check: None, empty string, or whitespace-only string are all falsy
    beneficiary_name = state.beneficiary_name if state.beneficiary_name and state.beneficiary_name.strip() else None
    beneficiary_account = state.beneficiary_account if state.beneficiary_account and state.beneficiary_account.strip() else None
    
    if beneficiary_name and beneficiary_account:
        collected.append(f"**Beneficiary:** {beneficiary_name} (Account: {beneficiary_account})")
    elif beneficiary_name:
        collected.append(f"**Beneficiary Name:** {beneficiary_name}")
    elif beneficiary_account:
        collected.append(f"**Beneficiary Account:** {beneficiary_account}")
    
    # Country
    if state.country and state.country.strip():
        collected.append(f"**Country:** {state.country}")
    
    # Delivery method
    if state.delivery_method and state.delivery_method.strip():
        collected.append(f"**Delivery Method:** {state.delivery_method}")
    
    if collected:
        return "Here's what I have so far:\n" + "\n".join(f"- {item}" for item in collected)
    return ""


def _next_missing_question(state: SendMoneyState) -> str:
    """Generate a natural question for the next missing field."""
    formats = get_expected_formats()
    
    if state.amount is None:
        return "How much would you like to send?"
    if state.currency is None:
        return "What currency would you like to use? (e.g., USD, MXN, COP, HNL, DOP, NIO, GTQ)"
    if state.beneficiary_account is None:
        if state.beneficiary_name:
            # We have the name, just need the account number
            return f"Please provide the account number for {state.beneficiary_name}. Expected format: {formats['beneficiary_account']}"
        else:
            # No name or account, ask for either
            return f"Who is the recipient? Please provide the beneficiary's name or account number. Account number format: {formats['beneficiary_account']}"
    if state.country is None:
        return f"Which country should the money be sent to? Supported: {', '.join(sorted(COUNTRY_CURRENCY_MAP.keys()))}"
    if state.delivery_method is None:
        return "How would you like the money to be delivered? (Bank Transfer, Mobile Wallet, Cash Pickup, or Card)"
    return "Is there anything else you'd like to update?"


def get_transfer_summary(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Gets the current transfer summary with all collected information.
    
    Args:
        tool_context: ADK's ToolContext providing access to session state
    
    Returns:
        A dictionary containing all collected transfer information
    """
    state_dict = _get_state_from_context(tool_context)
    state = _state_to_send_money_state(state_dict)
    return state.get_summary()


def send_money(tool_context: ToolContext) -> str:
    """
    Sends the money transfer with the collected information.
    This is a simulated transfer - in production, this would call a real payment API.
    
    Args:
        tool_context: ADK's ToolContext providing access to session state
    
    Returns:
        Confirmation message with transfer details
    """
    state_dict = _get_state_from_context(tool_context)
    state = _state_to_send_money_state(state_dict)
    
    # Debug: Log current state for troubleshooting
    current_state = {
        'amount': state.amount,
        'currency': state.currency,
        'beneficiary_account': state.beneficiary_account,
        'beneficiary_name': state.beneficiary_name,
        'country': state.country,
        'delivery_method': state.delivery_method,
    }
    
    # Verify all required information is present
    if not state.is_complete():
        missing = []
        if state.amount is None:
            missing.append("amount")
        if state.currency is None:
            missing.append("currency")
        if state.beneficiary_account is None:
            missing.append("beneficiary account")
        if state.country is None:
            missing.append("country")
        if state.delivery_method is None:
            missing.append("delivery method")
        
        # Return detailed error with current state for debugging
        # DO NOT clear state on failure - keep it so user can fix missing fields
        return (
            f"❌ Cannot send transfer yet. Missing information: {', '.join(missing)}.\n\n"
            f"Current information collected:\n"
            f"- Amount: {current_state.get('amount', 'Not provided')}\n"
            f"- Currency: {current_state.get('currency', 'Not provided')}\n"
            f"- Beneficiary Account: {current_state.get('beneficiary_account', 'Not provided')}\n"
            f"- Beneficiary Name: {current_state.get('beneficiary_name', 'Not provided')}\n"
            f"- Country: {current_state.get('country', 'Not provided')}\n"
            f"- Delivery Method: {current_state.get('delivery_method', 'Not provided')}\n\n"
            f"Please provide the missing information using collect_transfer_details, then try sending again."
        )
    
    # Generate a fake transaction ID
    import random
    transaction_id = f"TXN{random.randint(100000, 999999)}"
    
    # Simulate sending the money
    summary = state.get_summary()
    
    beneficiary_display = f"{summary['beneficiary_name']} ({summary['beneficiary_account']})" if summary['beneficiary_name'] else summary['beneficiary_account']
    confirmation_message = (
        f"✅ ✅ ✅ Transfer Successful!\n\n"
        f"**Transaction ID:** {transaction_id}\n"
        f"**Amount Sent:** {summary['amount']} {summary['currency']}\n"
        f"**Recipient:** {beneficiary_display}\n"
        f"**Destination:** {summary['country']}\n"
        f"**Delivery Method:** {summary['delivery_method']}\n\n"
        f"Your money has been sent successfully! The recipient should receive it within 1-3 business days "
        f"depending on the delivery method.\n\n"
        f"Thank you for using our service!"
    )
    
    # Reset state after successful transfer (only if transfer was successful)
    # Clear state by deleting all keys
    if tool_context.state is not None:
        # State is a dict-like object, clear it by deleting all keys
        # Get keys safely - State object might not have .keys() method
        try:
            # Try to get keys using .keys() method
            if hasattr(tool_context.state, 'keys'):
                keys_to_delete = list(tool_context.state.keys())
            else:
                # Fallback: use known field names
                keys_to_delete = ['amount', 'currency', 'beneficiary_account', 'beneficiary_name', 'country', 'delivery_method']
        except (AttributeError, TypeError):
            # If .keys() doesn't work, use known field names
            keys_to_delete = ['amount', 'currency', 'beneficiary_account', 'beneficiary_name', 'country', 'delivery_method']
        
        for key in keys_to_delete:
            try:
                if key in tool_context.state:
                    del tool_context.state[key]
            except (KeyError, AttributeError, TypeError):
                # Key might not exist or state might not support deletion
                pass
    
    return confirmation_message

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from typing import Optional, Dict, Any
from .send_money_agent import (
    collect_transfer_details,
    send_money,
)

#MODEL = "gemini-2.0-flash-exp"
MODEL = "gemini-2.5-flash"
# Store tool responses to use them directly instead of LLM processing
# We use a simple approach: store the last tool response and use it in after_model_callback
_last_tool_response = None

def after_tool_callback(*, tool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Store tool responses so we can use them directly instead of LLM processing.
    This runs AFTER the tool executes but BEFORE the LLM processes it.
    """
    # Get the tool name
    if hasattr(tool, '__name__'):
        tool_name = tool.__name__
    elif hasattr(tool, 'name'):
        tool_name = tool.name
    else:
        tool_name = str(tool)
    
    # Check if this is one of our tools that returns a complete response
    if tool_name in ['collect_transfer_details', 'send_money']:
        # Extract the result from the response
        tool_result = tool_response.get('result', '') if isinstance(tool_response, dict) else str(tool_response)
        
        # Only intercept tool responses that are NOT just questions
        # Questions like "How much would you like to send?" should be handled by the LLM normally
        # to avoid infinite loops where the agent calls the tool repeatedly
        question_indicators = [
            'how much', 'how would', 'what', 'which', 'who is', 'please provide',
            'would you like', 'do you want', 'can you', 'could you'
        ]
        tool_result_lower = str(tool_result).lower()
        
        # If the tool response is just a question (starts with question indicators), 
        # don't intercept it - let the LLM handle it normally
        is_just_question = any(tool_result_lower.strip().startswith(indicator) for indicator in question_indicators)
        
        if not is_just_question:
            # Store the tool result globally (simple approach - we'll use it in after_model_callback)
            global _last_tool_response
            _last_tool_response = tool_result
    
    return tool_response


def after_model_callback(*, callback_context: CallbackContext, llm_response) -> Optional:
    """
    Intercept model responses and replace them with tool responses when available.
    This runs AFTER the LLM generates a response.
    
    Why we need both callbacks:
    - after_tool_callback: Captures the tool response (runs after tool, before LLM)
    - after_model_callback: Replaces LLM response with tool response (runs after LLM)
    
    ADK's flow: Tool → after_tool_callback → LLM processes → after_model_callback → Final response
    We intercept at both points to ensure the tool response is used verbatim.
    """
    global _last_tool_response
    
    # If we have a stored tool response, use it instead of the LLM's response
    if _last_tool_response is not None:
        tool_result = _last_tool_response
        _last_tool_response = None  # Clear it after use
        
        # Replace the llm_response content with our tool result
        # We need to replace the entire part to avoid oneof conflicts (data vs text)
        try:
            if hasattr(llm_response, 'content') and llm_response.content is not None:
                if hasattr(llm_response.content, 'parts') and llm_response.content.parts:
                    part = llm_response.content.parts[0]
                    
                    # Check if part has 'data' field set - if so, we must replace the entire part
                    # to avoid oneof conflict (can't have both 'data' and 'text' set)
                    has_data = False
                    if isinstance(part, dict):
                        has_data = 'data' in part and part.get('data') is not None
                    elif hasattr(part, 'data'):
                        try:
                            has_data = part.data is not None
                        except:
                            pass
                    
                    # If data is set, replace the entire part to avoid oneof conflict
                    if has_data:
                        # Replace with a new part containing only text
                        llm_response.content.parts[0] = {'text': tool_result}
                    elif isinstance(part, dict):
                        # It's a dict without data, replace it entirely
                        llm_response.content.parts[0] = {'text': tool_result}
                    else:
                        # It's a protobuf-like object, try to clear data first, then set text
                        if hasattr(part, 'data'):
                            # Try to clear via ClearField (protobuf method)
                            if hasattr(part, 'ClearField'):
                                try:
                                    part.ClearField('data')
                                except:
                                    pass
                            # Also try setting to None
                            try:
                                part.data = None
                            except:
                                pass
                        # Now set the text field
                        if hasattr(part, 'text'):
                            try:
                                part.text = tool_result
                            except:
                                # If setting text fails, replace the part
                                llm_response.content.parts[0] = {'text': tool_result}
                        else:
                            # Can't set text, replace the part
                            llm_response.content.parts[0] = {'text': tool_result}
                else:
                    # If no parts, create parts list
                    llm_response.content.parts = [{'text': tool_result}]
        except Exception as e:
            # If modification fails, log but don't crash
            # The original response will be used
            pass
    
    # Return the (possibly modified) llm_response object
    return llm_response


root_agent = LlmAgent(
        name="send_money_agent",
        model=MODEL, 
        description="Agent to help users send money.",
        instruction=(
            "You are a helpful and friendly assistant that helps users send money. "
            "Be natural, conversational, and human-like in your interactions.\n\n"
            "YOUR ROLE:\n"
            "Collect the following information in a natural, conversational way: "
            "1. Amount to send\n"
            "2. Currency (e.g., USD, EUR, GBP)\n"
            "3. Beneficiary account number (the recipient's account - primary identifier)\n"
            "4. Beneficiary name (optional, attached to account - can be looked up from contacts)\n"
            "5. Destination country\n"
            "6. Delivery method (Bank Transfer, Mobile Wallet, Cash Pickup, or Card)\n\n"
            "CRITICAL: WHEN TO USE TOOLS\n"
            "DO NOT call ANY tools (including collect_transfer_details) for:\n"
            "- Pure greetings (just 'hello', 'hi')\n"
            "- General requests like 'send money', 'I want to send money', 'help me send money'\n"
            "- Vague requests that mention ONLY a name without other details:\n"
            "  * 'send money to john' - TOO VAGUE (no amount, no account, no country)\n"
            "  * 'I want to send money to john' - TOO VAGUE (no amount, no account, no country)\n"
            "  * 'send 100 to john' - TOO VAGUE (no account number, no country, no currency)\n"
            "  * 'send money to someone' - TOO VAGUE\n"
            "- Any message that does NOT contain MULTIPLE SPECIFIC transfer details (you need at least 2-3 clear pieces of information)\n"
            "- Casual conversation with no transfer information\n\n"
            "IMPORTANT: A request with ONLY a name (like 'I want to send money to john') is TOO VAGUE. "
            "You need MULTIPLE pieces of information before calling collect_transfer_details:\n"
            "- At minimum: amount + beneficiary name/account + country, OR\n"
            "- At minimum: amount + currency + beneficiary account, OR\n"
            "- Other combinations with at least 2-3 clear details\n\n"
            "If a request only has ONE piece of information (just a name, or just an amount, or just 'send money'), "
            "DO NOT call collect_transfer_details. Instead, respond conversationally and ask for more specific information.\n\n"
            "For greetings or vague/general requests, respond conversationally WITHOUT calling any tools. "
            "Say something like: 'Hi! I can help you send money. I'll need several details to process the transfer, and we'll go step by step. "
            "Let's start with the beneficiary's full name and account number.'\n\n"
            "ONLY call collect_transfer_details when the user's message contains MULTIPLE CLEAR, SPECIFIC transfer details:\n"
            "You need AT LEAST 2-3 of these pieces of information:\n"
            "- Amount (e.g., 'send $100', 'I want to send 500', '200 dollars')\n"
            "- Currency (e.g., 'USD', 'MXN', 'pesos', 'dollars', 'quetzales', 'lempiras')\n"
            "- Beneficiary name AND account number (e.g., 'John Smith AC123456', 'account ACC-123456', 'Daniela Varela 203933773')\n"
            "- Country (e.g., 'Mexico', 'Honduras', 'Colombia', 'Guatemala', 'Nicaragua', 'El Salvador', 'República Dominicana')\n"
            "- Delivery method (e.g., 'bank transfer', 'mobile wallet', 'card')\n\n"
            "EXAMPLES of when to CALL the tool:\n"
            "- 'Send $500 USD to John Smith AC123456 in Colombia' - has amount, currency, name, account, country\n"
            "- 'I want to send 200 dollars to account AC987654 in Mexico' - has amount, currency, account, country\n"
            "- 'Send $100 to Daniela Varela 203933773 in Colombia via Card' - has amount, name, account, country, method\n\n"
            "EXAMPLES of when NOT to call the tool (respond conversationally instead):\n"
            "- 'I want to send money to john' - only has a name, too vague\n"
            "- 'Send $100' - only has amount, need more info\n"
            "- 'Send money' - no specific details\n"
            "- 'Send to John' - only has a name, too vague\n\n"
            "IMPORTANT: If the user just says 'send money' or greets you, DO NOT call collect_transfer_details. "
            "Just respond conversationally and guide them to provide the first piece of information.\n\n"
            "SUPPORTED COUNTRIES AND CURRENCIES:\n"
            "- MEXICO → MXN (Mexican Peso / Pesos Mexicanos)\n"
            "- HONDURAS → HNL (Honduran Lempira / Lempiras)\n"
            "- REPUBLICA DOMINICANA / DOMINICAN REPUBLIC → DOP (Dominican Peso / Pesos Dominicanos)\n"
            "- NICARAGUA → NIO (Nicaraguan Córdoba / Córdobas)\n"
            "- COLOMBIA → COP (Colombian Peso / Pesos Colombianos)\n"
            "- EL SALVADOR → USD (US Dollar / Dólares)\n"
            "- GUATEMALA → GTQ (Guatemalan Quetzal / Quetzales)\n\n"
            "IMPORTANT: If a message contains BOTH a greeting AND transfer information, call collect_transfer_details "
            "to capture the information immediately. For example, 'Hi, I want to send $200 to John' - call the tool!\n\n"
            "TOOL DESCRIPTIONS:\n"
            "- collect_transfer_details: Use when user provides transfer information. "
            "If multiple contacts match a name, this tool will show options and ask 'Which one?'. "
            "The user's next response (e.g., 'the first one', '1', or a full name) will be handled automatically. "
            "This tool automatically shows collected information at each step, so you don't need to call it just to show a summary.\n"
            "- send_money: Use when user confirms they want to send the money (after all info is collected)\n\n"
            "CRITICAL: TOOL RESPONSES\n"
            "When collect_transfer_details returns a response, USE IT VERBATIM. Do NOT paraphrase, summarize, or modify it. "
            "The tool response already includes:\n"
            "- A formatted list of collected information (e.g., 'Here's what I have so far: - **Beneficiary:** ...')\n"
            "- The next question to ask\n"
            "Simply return the tool's response exactly as provided. Do not add your own interpretation or additional text.\n\n"
            "CONVERSATION STYLE:\n"
            "- Respond naturally to greetings without calling tools\n"
            "- Be friendly and conversational\n"
            "- When someone says 'hello', 'hi', 'send money', or 'I want to send money', greet them back and explain you can help. "
            "Then proactively say: 'I'll need several details to process the transfer, and we'll go step by step. "
            "Let's start with the beneficiary's full name and account number.' "
            "DO NOT call collect_transfer_details for these messages - just respond conversationally.\n"
            "- Only use tools when you detect actual transfer information in their message\n"
            "- When collect_transfer_details shows contact options, just wait for the user's selection - no need to call another tool\n"
            "- When all information is collected, offer to send the money using the send_money tool\n"
            "- Guide the conversation naturally toward collecting the needed information\n"
            "- If the user provides invalid values (wrong country, currency, or delivery method), the tool will guide them with the correct format - "
            "just continue the conversation naturally\n"
            "- If the user uses inappropriate language, profanity, or becomes abusive, politely end the conversation with: "
            "'I apologize, but I'm not able to continue this conversation. Please contact our customer service team for assistance. Have a good day!'\n\n"
            "Remember: Think like a human assistant. If someone just says 'hi', you say 'hi' back and ask how you can help with the money transfer. "
            "You don't need to call a tool to have a conversation!"
        ),
        tools=[
            collect_transfer_details,
            send_money
        ],
        after_tool_callback=after_tool_callback,
        after_model_callback=after_model_callback
    )
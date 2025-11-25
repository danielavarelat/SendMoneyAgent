# Send Money Agent

A conversational agent built with Google ADK that helps users send money by collecting transfer details through natural conversation.

## Overview

This agent collects the necessary information to initiate a money transfer:
- **Amount** to send
- **Currency** (USD, MXN, COP, HNL, DOP, NIO, GTQ)
- **Beneficiary account number** (primary identifier, e.g., "AC12629233", "ACC-123456")
- **Beneficiary name** (optional, for verification)
- **Destination country** (MEXICO, HONDURAS, REPUBLICA DOMINICANA, NICARAGUA, COLOMBIA, EL SALVADOR, GUATEMALA)
- **Delivery method** (Bank Transfer, Mobile Wallet, Cash Pickup, or Card)

The agent handles greetings naturally, manages state across conversation turns, handles corrections, validates input, and provides clear error messages with expected formats.

## Features

- **Natural Conversation**: Handles greetings and vague requests conversationally without calling tools
- **Smart Tool Triggering**: Only calls tools when user provides multiple specific details (not just a name or single piece of info)
- **State Management**: Maintains conversation state across multiple turns using ADK's ToolContext
- **Correction Handling**: Allows users to update previously provided information (e.g., "change amount to 200")
- **Context-Aware Extraction**: Extracts fields from user input with validation
- **Input Validation**: Validates currency, country, and delivery method with helpful error messages
- **Format Guidance**: Provides expected formats when asking for account numbers and other fields
- **Collected Info Display**: Always shows what information has been collected before asking for the next field

## Supported Countries and Currencies

- **MEXICO** → MXN (Mexican Peso)
- **HONDURAS** → HNL (Honduran Lempira)
- **REPUBLICA DOMINICANA** / **DOMINICAN REPUBLIC** → DOP (Dominican Peso)
- **NICARAGUA** → NIO (Nicaraguan Córdoba)
- **COLOMBIA** → COP (Colombian Peso)
- **EL SALVADOR** → USD (US Dollar)
- **GUATEMALA** → GTQ (Guatemalan Quetzal)

## Prerequisites

- Python 3.10+
- Google ADK >=0.1.0
- Google API Key with Gemini API access

## Installation

1. **Navigate to the FelixAgent directory:**
   ```bash
   cd FelixAgent
   ```

2. **Set up a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install the package in editable mode (so ADK can discover it):**
   ```bash
   pip install -e .
   ```

5. **Set up your environment variables:**
   
   Create a `.env` file in the project root (`agents/` directory):
   ```
   GOOGLE_API_KEY=your-api-key-here
   ```
   
   Or export it in your shell:
   ```bash
   export GOOGLE_API_KEY="your-api-key-here"
   ```

## Usage

Run `adk web` from the project root (`agents/` directory):

```bash
cd agents
adk web
```

ADK will automatically discover the agent by reading `pyproject.toml` in the `FelixAgent/` subdirectory.

### Testing

Run the test suite:

```bash
cd FelixAgent
python test_agent.py
```

## How It Works

1. **Agent Initialization**: The `root_agent` in `agent.py` is an `LlmAgent` with tools and callbacks
2. **Tool Functions**: Located in `send_money_agent.py`:
   - `collect_transfer_details`: Extracts and validates transfer information, shows collected info at each step
   - `send_money`: Executes the money transfer with collected information
   - `get_transfer_summary`: Helper function (not exposed as a tool) that returns a summary of collected information
3. **State Management**: Uses ADK's `ToolContext.state` to persist conversation state
4. **Callbacks**: 
   - `after_tool_callback`: Captures tool responses (only for non-question responses to avoid loops)
   - `after_model_callback`: Replaces LLM responses with tool responses verbatim (handles oneof conflicts)
5. **Extraction**: Context-aware extraction prioritizes fields based on what's missing in the conversation

## Example Conversation

```
User: Hi
Agent: Hi! I can help you send money. I'll need several details to process the transfer, 
       and we'll go step by step. Let's start with the beneficiary's full name and account number.

User: Daniela Varela AC2938423
Agent: Here's what I have so far:
       - **Beneficiary:** Daniela Varela (Account: AC2938423)
       How much would you like to send?

User: 100 USD
Agent: Here's what I have so far:
       - **Amount:** 100.0 USD
       - **Beneficiary:** Daniela Varela (Account: AC2938423)
       Which country should the money be sent to? Supported: COLOMBIA, DOMINICAN REPUBLIC, 
       EL SALVADOR, GUATEMALA, HONDURAS, MEXICO, NICARAGUA, REPUBLICA DOMINICANA

User: COLOMBIA
Agent: Here's what I have so far:
       - **Amount:** 100.0 USD
       - **Beneficiary:** Daniela Varela (Account: AC2938423)
       - **Country:** COLOMBIA
       How would you like the money to be delivered? (Bank Transfer, Mobile Wallet, Cash Pickup, or Card)

User: Card
Agent: Great, I have everything!
       **Amount:** 100.0 USD
       **Beneficiary:** Daniela Varela (Acct AC2938423)
       **Country:** COLOMBIA
       **Delivery Method:** Card
       Would you like to proceed with the transfer?

User: Yes
Agent: ✅ ✅ ✅ Transfer Successful!
       **Transaction ID:** TXN123456
       **Amount Sent:** 100.0 USD
       **Recipient:** Daniela Varela (AC2938423)
       **Destination:** COLOMBIA
       **Delivery Method:** Card
       ...
```

## Troubleshooting

### `adk web` doesn't find the agent

**Problem:** Running `adk web` shows "No agents found" or similar error.

**Solution:**
1. Make sure you're in the project root (`agents/` directory), not inside `FelixAgent/`
2. Verify `FelixAgent/pyproject.toml` exists and contains:
   ```toml
   [tool.adk]
   agent-module = "agent"
   agent-variable = "root_agent"
   ```
3. Make sure you've installed the package: `cd FelixAgent && pip install -e .`
4. Verify `FelixAgent/agent.py` exists and contains `root_agent`
5. Try running `python -c "from FelixAgent.agent import root_agent; print('Agent found!')"` to test import

### Import errors

**Problem:** `ModuleNotFoundError` or import errors.

**Solution:**
1. Make sure you've installed dependencies: `pip install -r requirements.txt`
2. Install the package: `pip install -e .` (from `FelixAgent/` directory)
3. Check that all required files exist: `agent.py`, `send_money_agent.py`, etc.

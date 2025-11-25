# Send Money Agent

A self-contained conversational agent built with Google ADK that helps users send money by collecting transfer details through natural conversation.

## 📁 Project Structure

**IMPORTANT:** This project has a specific directory structure:

```
apps/                          # Parent directory (for Docker)
├── Dockerfile                 # Docker build file (builds from apps/)
├── docker-compose.yml         # Docker Compose configuration
└── FelixAgent/                # Main agent code directory
    ├── agent.py               # Root agent definition (root_agent)
    ├── send_money_agent.py    # Tool functions
    ├── send_money_state.py    # State management
    ├── utils.py               # Utilities
    ├── test_agent.py          # Test suite
    ├── pyproject.toml         # ADK configuration (agent discovery)
    ├── requirements.txt       # Python dependencies
    └── README.md              # This file
```

**Key Points:**
- All agent code is in the `FelixAgent/` subdirectory
- `pyproject.toml` is in `FelixAgent/` - this is where ADK looks for the agent
- Docker files are in the parent `apps/` directory
- For local development, work from the `FelixAgent/` directory
- For Docker, build from the `apps/` directory

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
- **Tool Response Handling**: Uses callbacks to ensure tool responses are shown verbatim (prevents infinite loops by not intercepting questions)

## Supported Countries and Currencies

- **MEXICO** → MXN (Mexican Peso)
- **HONDURAS** → HNL (Honduran Lempira)
- **REPUBLICA DOMINICANA** / **DOMINICAN REPUBLIC** → DOP (Dominican Peso)
- **NICARAGUA** → NIO (Nicaraguan Córdoba)
- **COLOMBIA** → COP (Colombian Peso)
- **EL SALVADOR** → USD (US Dollar)
- **GUATEMALA** → GTQ (Guatemalan Quetzal)

## Installation

### Option 1: Docker (Recommended for Self-Contained Solution)

**Note:** Docker files are in the parent `apps/` directory, not in `FelixAgent/`.

1. **Build and run with Docker Compose (from `apps/` directory):**
   ```bash
   cd /path/to/apps
   docker-compose up --build
   ```

2. **Or build and run manually:**
   ```bash
   cd /path/to/apps
   docker build -t send-money-agent .
   docker run -it --rm \
     -e GOOGLE_API_KEY="your-api-key-here" \
     -p 8080:8080 \
     send-money-agent
   ```

3. **Set your API key:**
   - Create a `.env` file with `GOOGLE_API_KEY=your-api-key-here`, or
   - Pass it as an environment variable: `-e GOOGLE_API_KEY="your-key"`

### Option 2: Local Installation

**IMPORTANT:** You must work from the `FelixAgent/` directory for local development.

1. **Navigate to the FelixAgent directory:**
   ```bash
   cd FelixAgent
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install the package in editable mode (so ADK can discover it):**
   ```bash
   pip install -e .
   ```

4. **Set up your environment variables:**
   ```bash
   export GOOGLE_API_KEY="your-api-key-here"
   ```
   
   Or create a `.env` file in the `FelixAgent/` directory:
   ```
   GOOGLE_API_KEY=your-api-key-here
   ```

## Usage

### Interactive Web Interface

**CRITICAL:** You must run `adk web` from the `FelixAgent/` directory where `pyproject.toml` is located.

```bash
# Navigate to FelixAgent directory
cd FelixAgent

# Make sure the package is installed
pip install -e .

# Run ADK web interface
adk web
```

ADK will automatically discover the agent by reading `pyproject.toml` in the current directory. The `pyproject.toml` file tells ADK:
- `agent-module = "agent"` - the module to import
- `agent-variable = "root_agent"` - the variable name in that module

**If `adk web` doesn't find the agent:**
1. Make sure you're in the `FelixAgent/` directory
2. Make sure `pyproject.toml` exists in the current directory
3. Make sure you've run `pip install -e .` to install the package
4. Check that `agent.py` exists and contains `root_agent`

### Testing

Run the test suite from the `FelixAgent/` directory:

```bash
cd FelixAgent
python test_agent.py
```

### Programmatic Usage

From the `FelixAgent/` directory:

```python
from agent import root_agent
# Use root_agent with ADK's runner or web interface
```

Or if installed as a package:

```python
from FelixAgent.agent import root_agent
# Use root_agent with ADK's runner or web interface
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

## Docker Deployment

### Building the Image

**IMPORTANT:** Build from the `apps/` directory (parent directory), not from `FelixAgent/`.

```bash
# Navigate to the apps/ directory (parent of FelixAgent/)
cd /path/to/apps

# Build the Docker image
docker build -t send-money-agent .
```

### Running the Container

```bash
# From the apps/ directory
cd /path/to/apps

docker run -it --rm \
  -e GOOGLE_API_KEY="your-api-key-here" \
  -p 8080:8080 \
  send-money-agent
```

### Using Docker Compose

```bash
# From the apps/ directory
cd /path/to/apps

# Set your API key in .env file (optional - can also use environment variable)
echo "GOOGLE_API_KEY=your-api-key-here" > .env

# Start the service
docker-compose up --build
```

## Development

### Running Tests

From the `FelixAgent/` directory:

```bash
cd FelixAgent
python test_agent.py
```

### Code Structure

- **`agent.py`**: Defines the `root_agent` (LlmAgent) with tools and callbacks
- **`send_money_agent.py`**: Contains all tool functions that the agent can call
- **`send_money_state.py`**: Defines the `SendMoneyState` dataclass for state management
- **`utils.py`**: Utility functions for extraction, validation, and formatting

## Requirements

- Python 3.10+ (as specified in `pyproject.toml`)
- Google ADK >=0.1.0
- Google API Key with Gemini API access

## Troubleshooting

### `adk web` doesn't find the agent

**Problem:** Running `adk web` shows "No agents found" or similar error.

**Solution:**
1. Make sure you're in the `FelixAgent/` directory (where `pyproject.toml` is located)
2. Verify `pyproject.toml` exists and contains:
   ```toml
   [tool.adk]
   agent-module = "agent"
   agent-variable = "root_agent"
   ```
3. Install the package: `pip install -e .` (from `FelixAgent/` directory)
4. Verify `agent.py` exists and contains `root_agent`
5. Try running `python -c "from agent import root_agent; print('Agent found!')"` to test import

### Docker container doesn't load agent

**Problem:** Docker container runs but ADK doesn't find the agent.

**Solution:**
1. Make sure you're building from the `apps/` directory (parent of `FelixAgent/`)
2. Check that the Dockerfile copies `FelixAgent/` correctly
3. Verify the Dockerfile runs `pip install -e .` in `/app/FelixAgent`
4. Check that the CMD runs `adk web` from `/app/FelixAgent` directory

### Import errors

**Problem:** `ModuleNotFoundError` or import errors.

**Solution:**
1. Make sure you've installed dependencies: `pip install -r requirements.txt`
2. Install the package: `pip install -e .` (from `FelixAgent/` directory)
3. Check that all required files exist: `agent.py`, `send_money_agent.py`, etc.

## License

This is a technical assessment solution.

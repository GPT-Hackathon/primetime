# Hello World Agent

A simple hello world agent built with Google ADK for testing deployment to Vertex AI Agent Engine.

## Overview

This agent demonstrates a basic ADK agent that can greet users and respond to simple queries. It's designed to be a minimal example for testing the ADK deployment workflow to Google Cloud Vertex AI.

## Project Structure

```
world_hello/
├── agent.py          # Agent definition with greet tool
├── test_local.py     # Local testing script
├── __init__.py       # Package initialization
├── .env              # Environment configuration (not in git)
├── requirements.txt  # Python dependencies (for pip users)
└── README.md         # This file
```

## Prerequisites

- Python 3.11 or higher
- Google Cloud account with Vertex AI API enabled
- Google Cloud project with billing enabled
- `gcloud` CLI installed and authenticated
- Either `uv` (recommended) or `pip` for package management

## Setup

### Option 1: Using `uv` (Recommended)

This project uses `uv` for package management. If you don't have `uv` installed:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

Then install dependencies:

```bash
# From the project root directory
cd /path/to/primetime
uv sync
```

### Option 2: Using `pip`

If you prefer using `pip`:

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd world_hello
pip install -r requirements.txt
```

## Configuration

### 1. Set up Google Cloud Authentication

Authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

### 2. Configure Environment Variables

Use checked in .env for hackathon 

OR

Create a `.env` file in the `world_hello` directory:

```bash
cd world_hello
cat > .env << EOF
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
EOF
```

**Important:** Replace `your-project-id` with your actual Google Cloud project ID.


## Usage

### Test Locally

Before deploying, test the agent locally to ensure everything works:

#### Using `uv`:

```bash
# From the project root directory
cd world_hello
uv run python test_local.py
```

#### Using `pip`:

```bash
# Make sure your virtual environment is activated
cd world_hello
python test_local.py
```

You should see output like:

```
Testing Hello World Agent locally...

 ### Created new session: test_session

User > Hello!
hello_world_agent > Hello, World! Welcome to the Hello World agent.

User > Greet Alice
hello_world_agent > Hello, Alice! Welcome to the Hello World agent.

User > What can you do?
hello_world_agent > I can greet people. Would you like me to greet someone?

✅ Test completed successfully!
Total events generated: 7
```

### Deploy to Vertex AI Agent Engine

Once local testing works, deploy to Vertex AI:

#### Prerequisites for Deployment

1. **Create a GCS staging bucket** (if you don't have one):

```bash
gsutil mb -p your-project-id -l us-central1 gs://your-staging-bucket
```

2. **Deploy using ADK CLI**:

```bash
# From the project root directory
adk deploy agent_engine \
    --project=your-project-id \
    --region=us-central1 \
    --staging_bucket gs://your-staging-bucket \
    --display_name "Hello World Agent" \
    world_hello
```

**Note:** Replace:
- `your-project-id` with your Google Cloud project ID
- `gs://your-staging-bucket` with your actual GCS bucket name

#### Verify Deployment

After deployment, you can test the deployed agent through:
- Vertex AI Console: https://console.cloud.google.com/vertex-ai/agent-builder
- API calls using the agent's endpoint
- ADK CLI tools

## What the Agent Does

The agent is a simple LLM-powered assistant that:

- **Greets users** with a friendly "Hello!" message
- **Uses the `greet` function** to greet specific people by name when asked
- **Answers questions** about its capabilities

### Example Queries

- "Hello!"
- "Greet Alice"
- "What can you do?"
- "Can you greet Bob?"

## How It Works

### Local Testing

When you run `test_local.py` locally:

1. The code runs on your machine
2. It authenticates with Google Cloud using Application Default Credentials
3. It makes API calls to Vertex AI's Gemini API (over the internet)
4. The LLM processes queries and decides when to call tools
5. Tool functions (like `greet`) execute locally
6. Results are returned to your terminal

**Key Point:** The agent code runs locally, but the LLM inference happens in Google Cloud. This allows you to test everything before deploying.

### Deployment

When you deploy with `adk deploy agent_engine`:

1. Your code is packaged and uploaded to Google Cloud
2. It runs in Vertex AI Agent Engine infrastructure
3. The agent is accessible via API endpoints
4. Google Cloud handles scaling, availability, and monitoring

## Troubleshooting

### Authentication Issues

If you get authentication errors:

```bash
# Re-authenticate
gcloud auth application-default login

# Verify your project
gcloud config get-value project
```

### Missing Dependencies

If you see import errors:

**Using `uv`:**
```bash
uv sync
```

**Using `pip`:**
```bash
pip install -r requirements.txt
```

### Vertex AI API Not Enabled

If you get API errors:

```bash
gcloud services enable aiplatform.googleapis.com
```

### Environment Variables Not Loading

Make sure your `.env` file exists and is in the `world_hello` directory:

```bash
cd world_hello
ls -la .env  # Should show the file
```

## Development

### Adding New Tools

To add new functionality, edit `agent.py`:

```python
def my_new_tool(param: str) -> str:
    """Description of what the tool does."""
    return f"Result: {param}"

root_agent = Agent(
    # ... existing config ...
    tools=[greet, my_new_tool],  # Add your tool here
)
```

### Testing Changes

Always test locally before deploying:

```bash
# Using uv
uv run python test_local.py

# Using pip
python test_local.py
```

## Resources

- [Google ADK Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/quickstart-adk)
- [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview)
- [ADK GitHub Repository](https://github.com/google/adk)

## License

[Add your license information here]

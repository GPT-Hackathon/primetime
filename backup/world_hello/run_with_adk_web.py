"""Run the Hello World agent locally and start ADK Web UI so you can view metrics.

Usage:
  python run_with_adk_web.py

This will:
- Start the ADK FastAPI web UI (default http://127.0.0.1:8000)
- Run the local agent and capture trace data/metrics
- Keep the web UI running so you can open the browser and inspect traces/metrics

Notes:
- Run this from the `world_hello/` directory (it's written to resolve the agents_dir
  relative to this file).
- You must have the project's dependencies installed in your environment.
"""

import os
import time
import threading
import asyncio
from dotenv import load_dotenv

# Load env and initialize Vertex AI as in test_local.py
load_dotenv()
import vertexai

vertexai.init(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
)

# Import OpenTelemetry for tracing
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor, SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.resources import Resource
from typing import Sequence
import json

# Import the ADK helper to create the FastAPI app and uvicorn to run it.
from google.adk.cli.fast_api import get_fast_api_app
import uvicorn

# Import the agent and runner
from agent import root_agent
from google.adk.runners import InMemoryRunner

# Global list to store span data for analysis
collected_spans = []


class ConfidenceCollectorExporter(SpanExporter):
    """Custom exporter to collect spans with confidence data."""

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Collect spans for later analysis."""
        for span in spans:
            if span.name == "call_llm":
                collected_spans.append(span)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

HOST = os.getenv("ADK_WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("ADK_WEB_PORT", "8000"))
AGENTS_DIR = os.getenv("ADK_AGENTS_DIR", "..")


def _start_adk_web():
    """Create the FastAPI app and run uvicorn (blocking)."""
    print(f"Starting ADK web UI (agents_dir={AGENTS_DIR}) on http://{HOST}:{PORT} ...")
    app = get_fast_api_app(
        agents_dir=AGENTS_DIR,
        web=True,
        host=HOST,
        port=PORT,
    )
    config = uvicorn.Config(app=app, host=HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)
    # This call blocks for the lifetime of the server.
    server.run()


async def test_agent_with_tracing():
    """Test the hello world agent locally with tracing enabled."""
    print("\n" + "="*60)
    print("Testing Hello World Agent locally with tracing enabled...")
    print("="*60 + "\n")

    runner = InMemoryRunner(agent=root_agent)

    test_queries = [
        "Hello!",
        "Greet Alice",
        "What can you do?",
    ]

    # Use run_debug which handles session creation automatically
    events = await runner.run_debug(
        user_messages=test_queries,
        user_id="test_user",
        session_id="test_session",
        verbose=True,  # Set to True to see tool calls and details
    )

    print("\n" + "="*60)
    print(f"✅ Test completed successfully!")
    print(f"Total events generated: {len(events)}")
    print("="*60 + "\n")

    # Print summary of events
    print("Event Summary:")
    print("-" * 60)
    for i, event in enumerate(events, 1):
        if event.content and event.content.parts:
            text = event.content.parts[0].text if event.content.parts[0].text else "[non-text content]"
            print(f"\n{i}. [{event.author}] {text[:80]}{'...' if len(text) > 80 else ''}")

    # Analyze confidence from collected spans
    print("\n" + "="*60)
    print("Confidence Analysis (Hallucination Detection):")
    print("="*60)
    analyze_collected_spans()

    await runner.close()
    return events


def analyze_collected_spans():
    """Analyze all collected spans for confidence scores."""
    if not collected_spans:
        print("⚠️  No LLM call spans collected")
        return

    print(f"\nAnalyzed {len(collected_spans)} LLM calls:\n")

    for i, span in enumerate(collected_spans, 1):
        attributes = dict(span.attributes) if span.attributes else {}

        # Get the LLM response
        llm_response_str = attributes.get('gcp.vertex.agent.llm_response')
        if not llm_response_str:
            continue

        try:
            llm_response = json.loads(llm_response_str)
            avg_logprobs = llm_response.get('avg_logprobs')

            if avg_logprobs is not None:
                confidence = calculate_confidence_score(avg_logprobs)
                risk_level, risk_msg = assess_hallucination_risk(avg_logprobs, confidence)

                # Get response text
                response_text = ""
                content = llm_response.get('content', {})
                parts = content.get('parts', [])
                if parts and isinstance(parts[0], dict):
                    response_text = parts[0].get('text', '[function call]')

                print(f"LLM Call #{i}:")
                print(f"  Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
                print(f"  📊 Confidence Score: {confidence:.1f}%")
                print(f"  📈 Avg Log Probability: {avg_logprobs:.4f}")
                print(f"  🚨 Hallucination Risk: {risk_level} - {risk_msg}")

                # Token usage
                usage = llm_response.get('usage_metadata', {})
                if usage:
                    print(f"  📝 Tokens: {usage.get('prompt_token_count', 0)} in / {usage.get('candidates_token_count', 0)} out")
                print()

        except json.JSONDecodeError as e:
            print(f"  ⚠️  Could not parse LLM response: {e}\n")


def calculate_confidence_score(avg_logprobs):
    """
    Convert average log probability to a confidence percentage.

    Log probabilities typically range from -infinity to 0:
    - 0.0 = 100% confidence (certainty)
    - -1.0 = ~37% confidence
    - -2.0 = ~14% confidence
    - -5.0 or lower = very low confidence
    """
    # Use exponential to convert logprob to probability
    # Then scale to percentage
    if avg_logprobs >= 0:
        return 100.0
    elif avg_logprobs < -5:
        return 0.0
    else:
        # e^(avg_logprobs) gives probability, multiply by 100 for percentage
        import math
        return min(100.0, max(0.0, math.exp(avg_logprobs) * 100))


def assess_hallucination_risk(avg_logprobs, confidence):
    """
    Assess hallucination risk based on confidence scores.

    Returns: (risk_level, description)
    """
    if avg_logprobs >= -0.5:
        return "🟢 LOW", "Model is highly confident in response"
    elif avg_logprobs >= -1.5:
        return "🟡 MODERATE", "Model has reasonable confidence"
    elif avg_logprobs >= -3.0:
        return "🟠 ELEVATED", "Lower confidence - verify facts"
    else:
        return "🔴 HIGH", "Very low confidence - likely hallucination"


def main():
    # Set up OpenTelemetry tracing to console
    resource = Resource.create({"service.name": "hello-world-agent"})
    provider = TracerProvider(resource=resource)

    # Add console exporter to see traces in terminal
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(console_exporter))

    # Add custom collector to capture confidence data
    confidence_collector = ConfidenceCollectorExporter()
    provider.add_span_processor(SimpleSpanProcessor(confidence_collector))

    # Set the global tracer provider
    trace.set_tracer_provider(provider)

    print("\n🚀 Starting ADK Web UI and Agent Test\n")

    # Start the ADK web server in a non-daemon thread so the process keeps running
    server_thread = threading.Thread(target=_start_adk_web, daemon=False)
    server_thread.start()

    # Give the server a moment to start
    time.sleep(2)
    print(f"\n✨ ADK web UI available at: http://{HOST}:{PORT}\n")

    # Run the local test to generate events/metrics that the web UI will show
    try:
        events = asyncio.run(test_agent_with_tracing())
        print(f"\n📊 Generated {len(events)} events - view them in the web UI!")
    except Exception as e:
        print(f"\n❌ Error while running agent test: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("Local test run finished.")
    print(f"The ADK web UI continues at: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop the server")
    print("="*60 + "\n")

    # Keep the process alive so the web UI remains accessible.
    try:
        server_thread.join()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down ADK web UI...")


if __name__ == "__main__":
    main()


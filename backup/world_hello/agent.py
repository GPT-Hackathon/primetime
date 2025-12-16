"""Simple Hello World agent for testing ADK deployment."""

from google.adk.agents.llm_agent import Agent


def greet(name: str = "World") -> str:
    """A simple greeting function.
    
    Args:
        name: The name to greet. Defaults to "World".
        
    Returns:
        A greeting message.
    """
    return f"Hello, {name}! Welcome to the Hello World agent."


# Create the root agent with a simple tool
root_agent = Agent(
    model='gemini-2.5-flash',
    name='hello_world_agent',
    description='A simple hello world agent that greets users.',
    instruction='You are a friendly assistant that greets users. When asked to greet someone, use the greet function.',
    tools=[greet],
)

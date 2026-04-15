from pydantic_ai.messages import ModelResponse, ToolCallPart


def extract_tool_calls(run_results) -> list[ToolCallPart]:
    """
    Extracts tool call parts from pydantic_ai run results or a list of messages.
    Works with both ModelResponse objects and raw lists of messages.
    """
    executed_tools = []

    # Handle both run_results object and a list of messages
    messages = (
        run_results.new_messages()
        if hasattr(run_results, "new_messages")
        else run_results
    )

    for message in messages:
        # Tool calls are made BY the model, so we look inside ModelResponses
        if isinstance(message, ModelResponse):
            for part in message.parts:
                # Isolate the specific parts that are tool calls
                if isinstance(part, ToolCallPart):
                    executed_tools.append(part)
    return executed_tools

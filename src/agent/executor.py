"""
Claude tool-use execution loop for the Covered Club analyst agent.
"""

import json
import os
from pathlib import Path
from typing import Any

import anthropic
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from src.agent.prompts import SYSTEM_PROMPT, build_data_context
from src.agent.tools import (
    ALL_SCHEMAS,
    tool_generate_chart,
    tool_list_available_data,
    tool_query_dataframe,
    tool_rerun_pipeline,
    tool_write_dashboard_page,
)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _dispatch(
    tool_name: str, tool_input: dict, dataframes: dict
) -> tuple[str, go.Figure | None]:
    """Execute a tool call and return (text_result, optional_figure)."""
    figure = None

    if tool_name == "list_available_data":
        result = tool_list_available_data(dataframes)

    elif tool_name == "query_dataframe":
        result = tool_query_dataframe(
            dataset=tool_input["dataset"],
            operation=tool_input["operation"],
            params=tool_input.get("params", {}),
            dataframes=dataframes,
        )

    elif tool_name == "generate_chart":
        figure = tool_generate_chart(
            dataset=tool_input["dataset"],
            chart_type=tool_input["chart_type"],
            x=tool_input["x"],
            y=tool_input["y"],
            title=tool_input["title"],
            color=tool_input.get("color"),
            top_n=tool_input.get("top_n"),
            dataframes=dataframes,
        )
        result = json.dumps(
            {"ok": True, "message": f"Chart '{tool_input['title']}' generated."}
        )

    elif tool_name == "rerun_pipeline":
        result = tool_rerun_pipeline(
            clpi_weights=tool_input.get("clpi_weights"),
            region_filter=tool_input.get("region_filter"),
            project_root=PROJECT_ROOT,
        )

    elif tool_name == "write_dashboard_page":
        result = tool_write_dashboard_page(
            page_name=tool_input["page_name"],
            page_title=tool_input["page_title"],
            page_code=tool_input["page_code"],
            project_root=PROJECT_ROOT,
        )

    else:
        result = json.dumps({"error": f"Unknown tool '{tool_name}'"})

    return result, figure


def run_agent(
    messages: list[dict],
    dataframes: dict,
) -> tuple[str, list[go.Figure], bool]:
    """
    Run the agent loop until Claude stops issuing tool calls.

    Returns:
        (final_text, figures, pipeline_was_rerun)
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        try:
            import streamlit as st

            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass
    if not api_key:
        return (
            "⚠️ **ANTHROPIC_API_KEY is not set.** Add it to your `.env` file or Streamlit Cloud secrets to use the analyst.",
            [],
            False,
        )

    client = anthropic.Anthropic(api_key=api_key)
    data_context = build_data_context(dataframes)
    system = SYSTEM_PROMPT + data_context

    figures: list[go.Figure] = []
    pipeline_rerun = False

    claude_messages = list(messages)

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=ALL_SCHEMAS,
            messages=claude_messages,
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]

        if not tool_calls:
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            final_text = "\n".join(text_blocks)
            return final_text, figures, pipeline_rerun

        claude_messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            try:
                result_text, figure = _dispatch(tc.name, tc.input, dataframes)
                if figure is not None:
                    figures.append(figure)
                if tc.name == "rerun_pipeline":
                    parsed = json.loads(result_text)
                    if parsed.get("ok"):
                        pipeline_rerun = True
            except Exception as exc:
                result_text = json.dumps({"error": str(exc)})

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result_text,
                }
            )

        claude_messages.append({"role": "user", "content": tool_results})

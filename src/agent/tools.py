"""
Tool definitions (JSON schema) and implementations for the Covered Club analyst agent.
Each tool has:
  - SCHEMA: dict passed to Claude as a tool definition
  - A Python function that executes the tool and returns a JSON-serialisable result or
    a plotly Figure (for generate_chart).
"""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Tool schemas ──────────────────────────────────────────────────────────────

LIST_AVAILABLE_DATA_SCHEMA = {
    "name": "list_available_data",
    "description": (
        "List all loaded datasets with their column names and row counts. "
        "Call this first if you are unsure what data is available."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

QUERY_DATAFRAME_SCHEMA = {
    "name": "query_dataframe",
    "description": (
        "Query a loaded dataset. Supports filtering, sorting, groupby aggregation, "
        "and top-N selection. Returns rows as a JSON array."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "dataset": {
                "type": "string",
                "description": "Dataset name: clpi, quintile, prize, gambling, gdhi, sex_by_la, household_composition, uc_claimants, gambling_venues, leisure_companies, gambling_spend_by_region",
                "enum": [
                    "clpi",
                    "quintile",
                    "prize",
                    "gambling",
                    "gdhi",
                    "sex_by_la",
                    "household_composition",
                    "uc_claimants",
                    "gambling_venues",
                    "leisure_companies",
                    "gambling_spend_by_region",
                ],
            },
            "operation": {
                "type": "string",
                "description": "Operation: describe, top_n, filter, groupby, sort, correlate",
                "enum": ["describe", "top_n", "filter", "groupby", "sort", "correlate"],
            },
            "params": {
                "type": "object",
                "description": (
                    "Operation-specific params. "
                    "top_n: {n, column, ascending}. "
                    "filter: {column, operator, value} where operator is one of eq,ne,gt,lt,gte,lte,contains. "
                    "groupby: {by, agg_column, agg_func} where agg_func is mean/sum/count/min/max. "
                    "sort: {column, ascending}. "
                    "correlate: {col_a, col_b}."
                ),
            },
        },
        "required": ["dataset", "operation"],
    },
}

GENERATE_CHART_SCHEMA = {
    "name": "generate_chart",
    "description": (
        "Generate a Plotly chart from a loaded dataset. "
        "Returns a chart identifier that will be rendered in the dashboard."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "dataset": {
                "type": "string",
                "description": "Dataset name: clpi, quintile, prize, gambling, gdhi, sex_by_la, household_composition, uc_claimants, gambling_venues, leisure_companies, gambling_spend_by_region",
                "enum": [
                    "clpi",
                    "quintile",
                    "prize",
                    "gambling",
                    "gdhi",
                    "sex_by_la",
                    "household_composition",
                    "uc_claimants",
                    "gambling_venues",
                    "leisure_companies",
                    "gambling_spend_by_region",
                ],
            },
            "chart_type": {
                "type": "string",
                "description": "Chart type",
                "enum": ["bar", "bar_h", "scatter", "line", "pie", "box", "heatmap"],
            },
            "x": {"type": "string", "description": "Column name for x-axis"},
            "y": {"type": "string", "description": "Column name for y-axis"},
            "color": {
                "type": "string",
                "description": "Optional column name for color grouping",
            },
            "title": {"type": "string", "description": "Chart title"},
            "top_n": {
                "type": "integer",
                "description": "If set, only use the top N rows sorted by y descending",
            },
        },
        "required": ["dataset", "chart_type", "x", "y", "title"],
    },
}

RERUN_PIPELINE_SCHEMA = {
    "name": "rerun_pipeline",
    "description": (
        "Re-run the data pipeline with custom CLPI weights and/or a region filter. "
        "This recomputes all output CSVs. "
        "Weights must sum to 1.0."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "clpi_weights": {
                "type": "object",
                "description": (
                    "Optional CLPI weight overrides. "
                    "Keys: deprivation, fuel_poverty, income_gap. Values: floats summing to 1.0."
                ),
                "properties": {
                    "deprivation": {"type": "number"},
                    "fuel_poverty": {"type": "number"},
                    "income_gap": {"type": "number"},
                },
            },
            "region_filter": {
                "type": "string",
                "description": "Optional region name to restrict analysis (e.g. 'North West')",
            },
        },
        "required": [],
    },
}

WRITE_DASHBOARD_PAGE_SCHEMA = {
    "name": "write_dashboard_page",
    "description": (
        "Write a new persistent Streamlit dashboard page to the pages/ directory. "
        "The page will appear in the app navigation immediately after the next reload. "
        "page_name should be a short snake_case identifier (no .py suffix)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_name": {
                "type": "string",
                "description": "File name without extension, e.g. 'north_west_deep_dive'",
            },
            "page_title": {
                "type": "string",
                "description": "Human-readable title shown in the page header",
            },
            "page_code": {
                "type": "string",
                "description": "Full valid Python / Streamlit source code for the page",
            },
        },
        "required": ["page_name", "page_title", "page_code"],
    },
}

ALL_SCHEMAS = [
    LIST_AVAILABLE_DATA_SCHEMA,
    QUERY_DATAFRAME_SCHEMA,
    GENERATE_CHART_SCHEMA,
    RERUN_PIPELINE_SCHEMA,
    WRITE_DASHBOARD_PAGE_SCHEMA,
]

# ── Tool implementations ──────────────────────────────────────────────────────


def _get_df(dataset: str, dataframes: dict) -> pd.DataFrame:
    df = dataframes.get(dataset)
    if df is None or df.empty:
        raise ValueError(f"Dataset '{dataset}' is not loaded or is empty.")
    return df.copy()


def tool_list_available_data(dataframes: dict) -> str:
    rows = []
    for name, df in dataframes.items():
        if df is not None and not df.empty:
            rows.append(
                {"dataset": name, "rows": len(df), "columns": df.columns.tolist()}
            )
        else:
            rows.append(
                {"dataset": name, "rows": 0, "columns": [], "note": "not loaded"}
            )
    return json.dumps(rows, indent=2)


def tool_query_dataframe(
    dataset: str, operation: str, params: dict, dataframes: dict
) -> str:
    params = params or {}
    df = _get_df(dataset, dataframes)

    if operation == "describe":
        result = df.describe(include="all").round(2).to_dict()
        return json.dumps(result)

    elif operation == "top_n":
        n = int(params.get("n", 10))
        col = params.get("column")
        asc = bool(params.get("ascending", False))
        if col and col in df.columns:
            df = df.sort_values(col, ascending=asc)
        return df.head(n).to_json(orient="records", indent=2)

    elif operation == "filter":
        col = params["column"]
        op = params["operator"]
        val = params["value"]
        ops = {
            "eq": df[col] == val,
            "ne": df[col] != val,
            "gt": df[col] > val,
            "lt": df[col] < val,
            "gte": df[col] >= val,
            "lte": df[col] <= val,
            "contains": df[col]
            .astype(str)
            .str.contains(str(val), case=False, na=False),
        }
        mask = ops.get(op)
        if mask is None:
            raise ValueError(f"Unknown operator '{op}'")
        return df[mask].head(50).to_json(orient="records", indent=2)

    elif operation == "groupby":
        by = params["by"]
        agg_col = params["agg_column"]
        agg_func = params.get("agg_func", "mean")
        result = df.groupby(by)[agg_col].agg(agg_func).reset_index().round(2)
        return result.to_json(orient="records", indent=2)

    elif operation == "sort":
        col = params["column"]
        asc = bool(params.get("ascending", False))
        return (
            df.sort_values(col, ascending=asc)
            .head(20)
            .to_json(orient="records", indent=2)
        )

    elif operation == "correlate":
        col_a = params["col_a"]
        col_b = params["col_b"]
        corr = df[[col_a, col_b]].corr().iloc[0, 1]
        return json.dumps({"col_a": col_a, "col_b": col_b, "pearson_r": round(corr, 4)})

    raise ValueError(f"Unknown operation '{operation}'")


def tool_generate_chart(
    dataset: str,
    chart_type: str,
    x: str,
    y: str,
    title: str,
    color: str | None,
    top_n: int | None,
    dataframes: dict,
) -> go.Figure:
    df = _get_df(dataset, dataframes)

    if top_n and y in df.columns:
        df = df.nlargest(top_n, y)

    kwargs = dict(x=x, y=y, title=title, labels={x: x, y: y})
    if color and color in df.columns:
        kwargs["color"] = color

    if chart_type == "bar":
        fig = px.bar(df, **kwargs)
    elif chart_type == "bar_h":
        kwargs["orientation"] = "h"
        fig = px.bar(df, **kwargs)
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
    elif chart_type == "scatter":
        fig = px.scatter(df, **kwargs)
    elif chart_type == "line":
        fig = px.line(df, **kwargs)
    elif chart_type == "pie":
        fig = px.pie(df, names=x, values=y, title=title)
    elif chart_type == "box":
        fig = px.box(df, **kwargs)
    elif chart_type == "heatmap":
        pivot = df.pivot_table(index=y, columns=x, aggfunc="mean")
        fig = px.imshow(pivot, title=title)
    else:
        raise ValueError(f"Unknown chart_type '{chart_type}'")

    fig.update_layout(margin=dict(l=40, r=20, t=50, b=40))
    return fig


def tool_rerun_pipeline(
    clpi_weights: dict | None,
    region_filter: str | None,
    project_root: Path,
) -> str:
    config_path = project_root / "config.py"
    config_src = config_path.read_text()

    override_lines = []
    if clpi_weights:
        total = sum(clpi_weights.values())
        if abs(total - 1.0) > 0.001:
            return json.dumps(
                {"ok": False, "error": f"Weights sum to {total:.3f}, must sum to 1.0"}
            )
        override_lines.append(
            f"CLPI_WEIGHTS = {{'deprivation': {clpi_weights['deprivation']}, "
            f"'fuel_poverty': {clpi_weights['fuel_poverty']}, "
            f"'income_gap': {clpi_weights['income_gap']}}}"
        )

    temp_config = project_root / "_agent_config_override.py"
    try:
        override_src = config_src
        if override_lines:
            for line in override_lines:
                key = line.split("=")[0].strip()
                import re

                override_src = re.sub(
                    rf"^{key}\s*=.*$", line, override_src, flags=re.MULTILINE
                )
        temp_config.write_text(override_src)

        env = {}
        if region_filter:
            env["AGENT_REGION_FILTER"] = region_filter

        result = subprocess.run(
            [sys.executable, str(project_root / "run_pipeline.py")],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120,
            env={**{}, **env} if env else None,
        )

        if result.returncode == 0:
            return json.dumps(
                {
                    "ok": True,
                    "stdout": result.stdout[-2000:],
                    "weights_used": clpi_weights,
                    "region_filter": region_filter,
                }
            )
        else:
            return json.dumps({"ok": False, "stderr": result.stderr[-2000:]})
    finally:
        if temp_config.exists():
            temp_config.unlink()


def tool_write_dashboard_page(
    page_name: str,
    page_title: str,
    page_code: str,
    project_root: Path,
) -> str:
    pages_dir = project_root / "pages"
    pages_dir.mkdir(exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in page_name)
    page_path = pages_dir / f"{safe_name}.py"
    page_path.write_text(page_code)

    return json.dumps(
        {
            "ok": True,
            "path": str(page_path),
            "page_title": page_title,
            "message": f"Page '{page_title}' written to pages/{safe_name}.py. Reload the app to see it in the sidebar.",
        }
    )

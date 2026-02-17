"""Chart detection and configuration.

This module analyzes PowerBI tool results to determine if data is suitable
for chart visualization and recommends appropriate chart types.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import pandas as pd


@dataclass
class ChartConfig:
    """Configuration for chart rendering."""
    chart_type: str  # 'bar', 'line', 'pie', 'metric', 'table'
    x_column: str
    y_columns: List[str]
    title: str
    format_as_currency: bool = False
    format_as_percentage: bool = False
    color_scheme: str = 'tableau10'


def extract_rows_from_result(result: Dict[str, Any]) -> Optional[List[Dict]]:
    """
    Extract row data from PowerBI tool result.

    PowerBI ExecuteQuery returns data in two possible formats:
    1. structuredContent.Rows (direct rows)
    2. structuredContent.Tables[0].Rows (tables with columns and rows)

    Args:
        result: Tool result dictionary from MCP client

    Returns:
        List of row dictionaries if present, None otherwise
    """
    if not isinstance(result, dict) or "structuredContent" not in result:
        return None

    structured = result["structuredContent"]
    if not isinstance(structured, dict):
        return None

    # Format 1: Direct Rows field
    if "Rows" in structured and isinstance(structured["Rows"], list):
        return structured["Rows"]

    # Format 2: Tables array with Columns and Rows
    if "Tables" in structured and isinstance(structured["Tables"], list):
        if len(structured["Tables"]) > 0:
            table = structured["Tables"][0]
            if isinstance(table, dict) and "Rows" in table and "Columns" in table:
                # Convert array rows to dict rows using column names
                rows_data = table["Rows"]
                columns = table["Columns"]

                if isinstance(rows_data, list) and isinstance(columns, list):
                    # Extract and clean column names
                    col_names = []
                    for i, col in enumerate(columns):
                        name = col.get("Name", f"Column{i}")
                        # Clean up DAX column names:
                        # "Machine Tools Products[Product Category]" -> "Product Category"
                        # "[Total Revenue]" -> "Total Revenue"
                        if '[' in name and ']' in name:
                            # Extract content between last [ and ]
                            name = name[name.rfind('[')+1:name.rfind(']')]
                        col_names.append(name)

                    # Convert each row array to dictionary
                    dict_rows = []
                    for row in rows_data:
                        if isinstance(row, list):
                            row_dict = {col_names[i]: row[i] for i in range(min(len(row), len(col_names)))}
                            dict_rows.append(row_dict)

                    return dict_rows

    return None


def is_chartable(result: Dict[str, Any]) -> bool:
    """
    Determine if tool result contains chart-worthy data.

    Criteria:
    - Has structuredContent.Rows field
    - At least one row present
    - At least one numeric column exists
    - Row count <= 1000 (performance threshold)

    Args:
        result: Tool result dictionary

    Returns:
        True if data is suitable for charting
    """
    rows = extract_rows_from_result(result)
    if not rows or len(rows) == 0:
        return False

    # Convert to DataFrame to analyze
    try:
        df = pd.DataFrame(rows)

        # Must have at least one numeric column
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) == 0:
            return False

        # Reasonable row count for performance
        if len(df) > 1000:
            return False

        return True
    except Exception:
        return False


def analyze_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Categorize DataFrame columns by data type.

    Args:
        df: pandas DataFrame

    Returns:
        Dictionary with 'numeric', 'datetime', and 'categorical' column lists
    """
    return {
        'numeric': list(df.select_dtypes(include=['number']).columns),
        'datetime': list(df.select_dtypes(include=['datetime']).columns),
        'categorical': list(df.select_dtypes(exclude=['number', 'datetime']).columns)
    }


def recommend_chart_type(df: pd.DataFrame, col_types: Dict[str, List[str]]) -> str:
    """
    Recommend chart type based on data shape and column types.

    Decision tree:
    - Single row → 'metric' (metric card)
    - Has datetime column → 'line' (time series)
    - Percentages sum to ~100 → 'pie'
    - Default → 'bar'

    Args:
        df: pandas DataFrame
        col_types: Column type categorization from analyze_columns()

    Returns:
        Recommended chart type string
    """
    row_count = len(df)

    # Single row → metric card
    if row_count == 1:
        return 'metric'

    # Has datetime column → line chart for time series
    if col_types['datetime']:
        return 'line'

    # Check for percentage data (sum to ~100)
    for col in col_types['numeric']:
        col_sum = df[col].sum()
        if 95 <= col_sum <= 105:  # Allow 5% tolerance
            return 'pie'

    # Default to bar chart
    return 'bar'


def detect_chart_opportunity(
    result: Dict[str, Any],
    user_query: Optional[str] = None
) -> Optional[ChartConfig]:
    """
    Analyze tool result and return chart configuration if chartable.

    This is the main entry point for chart detection. It:
    1. Checks if data is chartable
    2. Converts to DataFrame
    3. Analyzes columns
    4. Recommends chart type (auto or from user_query hint)
    5. Detects formatting needs (currency, percentage)
    6. Returns complete ChartConfig

    Args:
        result: Tool result dictionary from MCP client
        user_query: Optional user message to detect explicit chart type requests
                    (e.g. "show as pie chart" overrides auto-detection)

    Returns:
        ChartConfig if data is chartable, None otherwise
    """
    if not is_chartable(result):
        return None

    rows = extract_rows_from_result(result)
    df = pd.DataFrame(rows)
    col_types = analyze_columns(df)

    # Need at least one numeric column
    if not col_types['numeric']:
        return None

    # Determine y-axis column (first numeric column)
    y_columns = col_types['numeric'][:1]

    # Determine x-axis column (prefer datetime, then categorical, then first column)
    if col_types['datetime']:
        x_column = col_types['datetime'][0]
    elif col_types['categorical']:
        x_column = col_types['categorical'][0]
    else:
        x_column = df.columns[0]

    # Detect currency formatting by column name
    y_col_name = y_columns[0].lower()
    format_as_currency = any(
        word in y_col_name
        for word in ['revenue', 'sales', 'price', 'amount', 'cost']
    )

    # Auto-recommend chart type based on data shape
    chart_type = recommend_chart_type(df, col_types)

    # Override with explicit user request if present
    if user_query:
        query_lower = user_query.lower()
        if any(word in query_lower for word in ['pie', 'donut', 'doughnut']):
            chart_type = 'pie'
        elif any(word in query_lower for word in ['line', 'trend', 'over time', 'over the']):
            chart_type = 'line'
        elif 'bar' in query_lower:
            chart_type = 'bar'

    # Generate descriptive title
    if chart_type == 'metric':
        title = y_columns[0]
    else:
        title = f"{y_columns[0]} by {x_column}"

    return ChartConfig(
        chart_type=chart_type,
        x_column=x_column,
        y_columns=y_columns,
        title=title,
        format_as_currency=format_as_currency
    )

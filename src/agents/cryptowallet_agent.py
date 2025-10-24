from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import START
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import pandas as pd
from typing import Optional
from pydantic import BaseModel, Field
import requests
import re
import chainlit as cl
from datetime import datetime

from config import app_config
from agents.base_agent import BaseAgent


class State(TypedDict):
    messages: Annotated[list, add_messages]
    time_range: Optional[str] = None
    filtered_df: Optional[pd.DataFrame] = None
    operation: Optional[str] = None
    wallet_ids: Optional[list] = None
    insights: Optional[str] = None
    x_axis: Optional[list] = None
    y_axis: Optional[list] = None
    is_detailed_report: Optional[bool] = None


class Operation(BaseModel):
    operation: str = Field(
        description="Get the operation details which user is trying to do"
    )
    date_range: Optional[str] = Field(
        description="Get the date range from the user input"
    )
    is_detailed_report: Optional[bool] = Field(
        description="Is the user asking for detailed report or not", default=False
    )


class graph_coordinates(BaseModel):
    x_axis: list = Field(description="x axis values")
    y_axis: list = Field(description="y axis values")


class Cryptowallet(BaseAgent):
    def __init__(self):
        super().__init__(servers_to_use=[])
        self.state_schema = State
        self.model = Operation

    def condition(self, state: State) -> str:
        is_detailed_report = state["is_detailed_report"]
        if is_detailed_report:
            return "graph_node"
        else:
            return "agent"

    def extract_date_range_and_operation(self, state: State) -> State:
        self.logger.info(f"State message value is {state['messages']}")
        self.today_date = datetime.now()
        message = state.get("messages", [])
        system_message = SystemMessage(
            content=(
                (
                    "You are an agent extracts date range and operation details from the user input"
                    "The date range should be in the format "
                    "'From YYYY-MM-DD 00:00:00 To YYYY-MM-DD 23:59:59'. "
                    f"Take the reference as today's date {self.today_date} and "
                    "calculate the time range accordingly. "
                    "If no date range is mentioned, return today's date range. "
                    "If the input is like last 7 days, return the date range for last 7 days. "
                    "The operations that are available are creation, deposit, withdraw, transfer, "
                    "delete, error, get, transaction. "
                    "Map corresponding operation based on the user input in the message."
                    "From the user input, tell if the user is asking for detailed report or not. "
                    "Check only for the last message for that"
                    "Any values cannot be None"
                    "is_detailed_report - The possible values are True or False."
                )
            )
        )

        human_message = HumanMessage(
            content=(
                f"""Please extract the following:
    - operation: What is the Operation that needs to be filtered from the user input
    - date_range: What is the date range mentioned in the user input.
    - is_detailed_report: Is the user asking for additional details or not.
    True if the user is asking else false
    If no date range is mentioned, return today's date range
    Strictly the output of operation should be one of the following:
    creation, deposit, withdraw, transfer, delete, error, get, transaction.

    Here is the message:
    {message}
    """
            )
        )
        evaluator_messages = [system_message, human_message]

        eval_result = self.llm_structured_output.invoke(evaluator_messages)

        state["operation"] = eval_result.operation
        if state["operation"] is None:
            state["operation"] = "creation"
        state["time_range"] = eval_result.date_range
        state["is_detailed_report"] = eval_result.is_detailed_report
        self.logger.info(
            f"is_detailed_report in the eval: {eval_result.is_detailed_report}"
        )
        self.logger.info(f"Operation extracted: {eval_result.operation}")
        return state

    def query_wallet_data_from_loki(self, state: State) -> State:
        self.logger.info("Querying Loki based on user input filters")

        # Extract from state
        operation = state.get("operation")
        time_range = state.get("time_range")

        # Loki credentials
        LOKI_URL = app_config.loki_url
        USERNAME = app_config.loki_username
        PASSWORD = app_config.loki_password
        SERVICE_NAME = "cryptowallet"

        # Convert time range to Loki timestamps (nanoseconds)
        start_str = time_range.split("From ")[1].split(" To")[0].strip()
        end_str = time_range.split("To ")[1].strip()
        start = int(pd.to_datetime(start_str).timestamp() * 1e9)
        end = int(pd.to_datetime(end_str).timestamp() * 1e9)

        # Map operation to Loki query pattern
        operation_pattern_map = {
            "creation": "Created wallet",
            "transfer": "Transferred",
            "deposit": "Deposited",
            "withdraw": "Withdrew",
            "delete": "Deleted wallet",
            "get": "amount in wallet",
            "transaction": "Transferred" or "Deposited" or "Withdrew",
        }

        log_pattern = operation_pattern_map.get(operation, "")
        if operation == "error":
            log_selector = f'{{service_name="{SERVICE_NAME}"}} | detected_level="ERROR"'
        if operation == "transaction":
            log_selector = (
                f'{{service_name="{SERVICE_NAME}"}} |~ '
                '"Transferred" or "Deposited" or "Withdrew"'
            )
        else:
            log_selector = f'{{service_name="{SERVICE_NAME}"}} |= "{log_pattern}"'
        params = {
            "query": log_selector,
            "start": str(start),
            "end": str(end),
            "limit": "1000",  # Consider making this configurable
            "direction": "backward",
        }

        response = requests.get(
            LOKI_URL, params=params, auth=(USERNAME, PASSWORD), timeout=30
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch logs from Loki: {response.status_code}\n{response.text}"
            )

        data = response.json()
        log_rows = []

        # Reuse your existing parsing logic
        operation_pattern = re.compile(
            r"(?P<creation>Created wallet)|"
            r"(?P<transfer>Transferred)|"
            r"(?P<deposit>Deposited)|"
            r"(?P<withdraw>withdrew)|"
            r"(?P<delete>Deleted wallet)|"
            r"(?P<get>amount in wallet)|"
            r"(?P<error>ERROR|not found|failed)",
            re.IGNORECASE,
        )

        for result in data.get("data", {}).get("result", []):
            stream = result.get("stream", {})
            severity = stream.get("severity_text", "UNKNOWN")
            trace_id = stream.get("trace_id", "N/A")
            span_id = stream.get("span_id", "N/A")
            service = stream.get("service_name", "unknown")

            for ts, message in result.get("values", []):
                ts_sec = int(ts) / 1e9
                formatted_time = datetime.utcfromtimestamp(ts_sec).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                wallet_ids = re.findall(r"[a-f0-9\-]{36}", message)
                location_match = re.search(r"location\s+([A-Za-z]+)", message)
                location = location_match.group(1) if location_match else "unknown"

                user_match = re.search(r"username\s+(\w+)", message)
                username = user_match.group(1) if user_match else "unknown"

                match_operation = operation_pattern.search(message)
                op_type = None
                if match_operation:
                    for op_name, op_val in match_operation.groupdict().items():
                        if op_val:
                            op_type = op_name
                            break
                else:
                    op_type = "error" if severity == "ERROR" else "unknown"

                log_rows.append(
                    {
                        "Date": formatted_time,
                        "Status": severity,
                        "Service": service,
                        "Trace ID": trace_id,
                        "Span ID": span_id,
                        "Message": message.strip(),
                        "Location": location,
                        "user": username,
                        "Operation": op_type,
                        "Wallet IDs": wallet_ids,
                    }
                )

        df = pd.DataFrame(log_rows)
        # Save filtered df into state
        state["filtered_df"] = df.to_dict(orient="records")
        self.wallet_df = df  # Optional: still keep it for wallet-level analysis

        return state

    def process_insights(self, state: State, system_message: SystemMessage) -> State:
        """
        Common method to process insights with a given system message.

        Args:
            state: The current state dictionary
            system_message: The system message to append before LLM invocation

        Returns:
            Updated state with insights and messages
        """
        messages = state["messages"] + [system_message]
        response = self.llm.invoke(messages)

        if isinstance(response, AIMessage):
            state["messages"].append(response)
        else:
            state["messages"].append(AIMessage(content=str(response)))

        state["insights"] = response

        return state

    def fetch_result(self, state: State) -> State:
        filtered_records = state["filtered_df"]
        system_message = SystemMessage(
            content=(
                "You are an agent that fetches result based on the user input. "
                f"Correlate and give answer to the userinput with reference to these "
                f"records: {filtered_records}. "
                f"Answer question based on the data provided. "
                "If the user ask for detailed report or insights, you must include:\n\n"
                "Prefer direct answer if the user didnot request detailed report.\n"
                "Give detailed analysis only when the user ask. "
                "Include things like wallet level information, user level information, "
                "location level information, currency distribution, recomendations, "
                "anamoly in the detailed report along with other things."
            )
        )
        return self.process_insights(state, system_message)

    def group_by_date(self, state: State) -> State:
        df = self.wallet_df
        df["Date"] = pd.to_datetime(df["Date"])  # Convert to datetime

        if df["Date"].dt.date.nunique() == 1:
            # All entries on the same day -> group by 4-hour bucket
            df["Bucket"] = df["Date"].dt.floor("4H")  # Round down to nearest 4 hours
            grouped = df.groupby("Bucket").size().reset_index(name="count")

            # Create full 4-hour range for the day
            day = df["Date"].dt.date.iloc[0]
            time_range = pd.date_range(
                start=pd.Timestamp(f"{day} 00:00:00"),
                end=pd.Timestamp(f"{day} 23:59:59"),
                freq="4H",
            )

            # Reindex to fill missing buckets
            grouped = (
                grouped.set_index("Bucket")
                .reindex(time_range, fill_value=0)
                .rename_axis("Bucket")
                .reset_index()
            )

            # Format x and y axes
            grouped["x_axis"] = grouped["Bucket"].dt.strftime("%Y-%m-%d %H:%M")
            x_axis = grouped["x_axis"].tolist()
            y_axis = grouped["count"].tolist()

        else:
            df["DateOnly"] = df[
                "Date"
            ].dt.normalize()  # Keep it in datetime64, not Python date

            # Group by day
            grouped = df.groupby("DateOnly").size().reset_index(name="count")

            # Fill in missing dates
            date_range = pd.date_range(
                start=df["DateOnly"].min(), end=df["DateOnly"].max()
            )

            grouped = (
                grouped.set_index("DateOnly")
                .reindex(date_range, fill_value=0)
                .rename_axis("DateOnly")
                .reset_index()
            )
            x_axis = grouped["DateOnly"].dt.strftime("%Y-%m-%d").tolist()
            y_axis = grouped["count"].tolist()
        cl.user_session.set("x_axis", x_axis)
        cl.user_session.set("y_axis", y_axis)
        cl.user_session.set("operation", state["operation"])
        state["x_axis"] = x_axis
        state["y_axis"] = y_axis
        self.logger.info(f"x_axis extracted: {state['x_axis']}")
        self.logger.info(f"y_axis extracted: {state['y_axis']}")

        return state

    def add_nodes_to_graph(self, graph_builder, state: State):
        graph_builder.add_node(
            "extract_parameters", self.extract_date_range_and_operation
        )
        graph_builder.add_node("query_data", self.query_wallet_data_from_loki)
        graph_builder.add_node("fetch_result", self.fetch_result)
        graph_builder.add_node("group_by_date", self.group_by_date)
        graph_builder.add_edge(START, "extract_parameters")
        graph_builder.add_edge("extract_parameters", "query_data")
        graph_builder.add_edge("query_data", "fetch_result")
        graph_builder.add_conditional_edges(
            "fetch_result",
            self.condition,
            {"graph_node": "group_by_date", "agent": self.agent_node_name},
        )

        graph_builder.add_edge("group_by_date", self.agent_node_name)

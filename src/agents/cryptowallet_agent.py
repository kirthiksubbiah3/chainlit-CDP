from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import pandas as pd
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
import requests
import re

from config import app_config
from agents.base_agent import BaseAgent


class State(TypedDict):
    messages: Annotated[list, add_messages]
    time_range: Optional[str] = None
    filtered_df: Optional[pd.DataFrame] = None
    operation: Optional[str] = None
    wallet_ids: Optional[list] = None
    insights: Optional[str] = None


class Operation(BaseModel):
    operation: str = Field(
        description="Get the operation details which user is trying to do"
    )
    date_range: Optional[str] = Field(
        description="Get the date range from the user input"
    )


class Cryptowallet(BaseAgent):
    def __init__(self):
        super().__init__(servers_to_use=[])
        self.state_schema = State
        self.model = Operation

    def safe_tools_condition(self, state: State) -> str:
        operation = state.get("operation", None)
        if operation == "creation":
            return "creation"
        if operation == "transfer":
            return "transfer"
        if operation == "deposit":
            return "deposit"
        if operation == "withdraw":
            return "withdraw"
        if operation == "delete":
            return "delete"
        if operation == "error":
            return "error"
        if operation == "get":
            return "get"
        if operation == "transaction":
            return "transaction"
        return END

    def extract_date_range_and_operation(self, state: State) -> State:
        today_date = datetime.now()
        message = state.get("messages", [])
        system_message = SystemMessage(
            content=(
                (
                    "You are an agent extracts date range and operation details from the user input"
                    "The date range should be in the format "
                    "'From YYYY-MM-DD 00:00:00 To YYYY-MM-DD 23:59:59'. "
                    f"Take the reference as today's date {today_date} and "
                    "calculate the time range accordingly. "
                    "If no date range is mentioned, return today's date range. "
                    "If the input is like last 7 days, return the date range for last 7 days. "
                    "The operations that are available are creation, deposit, withdraw, transfer, "
                    "delete, error, get, transaction. "
                    "Map corresponding operation based on the user input in the message."
                )
            )
        )

        human_message = HumanMessage(
            content=(
                f"""Please extract the following:
    - operation: What is the Operation that needs to be filtered from the user input
    - date_range: What is the date range mentioned in the user input. """
                "If no date range is mentioned, return today's date range\n"
                "  Strictly the output of operation should be one of the following: "
                "creation, deposit, withdraw, transfer, delete, error, get, transaction.\n"
                f'Here is the message:\n"""{message}"""'
            )
        )

        evaluator_messages = [system_message, human_message]

        eval_result = self.llm_structured_output.invoke(evaluator_messages)

        state["operation"] = eval_result.operation
        if state["operation"] is None:
            state["operation"] = "creation"
        state["time_range"] = eval_result.date_range
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

        self.logger.info(f"Using Loki query: {log_selector}")

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
        state["filtered_df"] = None
        return state

    def transfer_operation(self, state: State) -> State:
        filtered_records = state.get("filtered_df", [])

        system_message = SystemMessage(
            content=(
                "You are a data analyst agent. You are given wallet transfer records "
                "in tabular format. "
                "Your job is to create a comprehensive insight report, "
                "NOT just answer the user's question. "
                f"Answer question based on the data {filtered_records}\n"
                "The currency types available are BTC, ETH, GBP, USD.\n"
                "From the data, see Message column to identify the currency type "
                "and the amount transferred"
                "Regardless of what the user asked earlier, you must include:\n\n"
                "1. Total number of transfer happened\n"
                "2. Locations where transaction has happened\n"
                "3. Top Wallet ID involved\n"
                "4. What are the currency type involved in transfer\n"
                "5. How much transfer happened in each currency type\n"
                "6. Anomalies or suspicious activities\n"
                "7. Any recommendation for further analysis\n"
                "\n"
                "⚠️ Do NOT return just a single sentence or count. "
                "Always return a detailed paragraph or bullets."
            )
        )
        return self.process_insights(state, system_message)

    def deposit_operation(self, state: State) -> State:
        filtered_records = state.get("filtered_df", [])

        system_message = SystemMessage(
            content=(
                "You are a data analyst agent. You are given wallet deposit records "
                "in tabular format. "
                "Your job is to create a comprehensive insight report, "
                "NOT just answer the user's question. "
                f"Answer question based on the data {filtered_records}"
                "The currency types available are BTC, ETH, GBP, USD. "
                "From the data, see Message column to identify the currency type "
                "and the amount transferred"
                "Regardless of what the user asked earlier, you must include:\n\n"
                "1. Total number of deposited happened\n"
                "2. Locations where transaction has happened\n"
                "3. Top Wallet ID involved\n"
                "4. What are the currency type involved in deposit\n"
                "5. How much deposit happened in each currency type\n"
                "6. Anomalies or suspicious activities\n"
                "7. Any recommendation for further analysis\n\n"
                "⚠️ Do NOT return just a single sentence or count. Always return a detailed "
                "paragraph or bullets."
            )
        )
        return self.process_insights(state, system_message)

    def withdraw_operation(self, state: State) -> State:
        filtered_records = state.get("filtered_df", [])

        system_message = SystemMessage(
            content=(
                "You are a data analyst agent. You are given wallet withdraw records in "
                "tabular format. "
                "Your job is to create a comprehensive insight report, "
                "NOT just answer the user's question. "
                f"Answer question based on the data {filtered_records}"
                "The currency types available are BTC, ETH, GBP, USD.\n"
                "From the data, see Message column to identify the currency type "
                "and the amount transferred"
                "Regardless of what the user asked earlier, you must include:\n\n"
                "1. Total number of withdraw happened\n"
                "2. Locations where withdraw has happened\n"
                "3. Top Wallet ID involved\n"
                "4. What are the currency type involved in withdrawal\n"
                "5. How much withdrawal happened in each currency type\n"
                "6. Anomalies or suspicious activities\n"
                "7. Any recommendation for further analysis\n\n"
                "⚠️ Do NOT return just a single sentence or count. "
                "Always return a detailed paragraph or bullets."
            )
        )
        return self.process_insights(state, system_message)

    def delete_operation(self, state: State) -> State:
        filtered_records = state.get("filtered_df", [])

        system_message = SystemMessage(
            content=(
                "You are a data analyst agent. You are given wallet delete records "
                "in tabular format. "
                "Your job is to create a comprehensive insight report, "
                "NOT just answer the user's question. "
                f"Answer question based on the data {filtered_records}"
                "1. Total number of delete operation happened\n"
                "2. Locations where delete operation has happened\n"
                "3. Top Wallet ID involved\n"
                "4. Anomalies or suspicious activities\n"
                "5. Any recommendation for further analysis\n\n"
                "⚠️ Do NOT return just a single sentence or count. "
                "Always return a detailed paragraph or bullets."
            )
        )
        return self.process_insights(state, system_message)

    def error_operation(self, state: State) -> State:
        filtered_records = state.get("filtered_df", [])

        system_message = SystemMessage(
            content=(
                "You are a data analyst agent. You are given wallet error records in tabular "
                "format. Your job is to create a comprehensive insight report, "
                "NOT just answer the user's question. "
                f"Answer question based on the data {filtered_records}"
                "1. Total number of error operation happened\n"
                "2. Locations where error operation has happened\n"
                "3. Top Wallet ID involved in error operation\n"
                "4. Anomalies or suspicious activities\n"
                "5. Highest location, user, currency where error is involved\n"
                "6. Any recommendation for further analysis\n\n"
                "⚠️ Do NOT return just a single sentence or count. "
                "Always return a detailed paragraph or bullets."
            )
        )
        return self.process_insights(state, system_message)

    def get_operation(self, state: State) -> State:
        filtered_records = state.get("filtered_df", [])

        system_message = SystemMessage(
            content=(
                "You are a data analyst agent. You are given wallet get records in tabular format. "
                "Your job is to create a comprehensive insight report, "
                "NOT just answer the user's question. "
                f"Answer question based on the data {filtered_records}"
                "1. Total number of get operation happened\n"
                "2. Locations where get operation has happened\n"
                "3. Top Wallet ID involved in get operation\n"
                "4. Currency details of the wallets where get operation has involved\n"
                "5. Anomalies or suspicious activities\n"
                "6. Any recommendation for further analysis\n\n"
                "⚠️ Do NOT return just a single sentence or count. "
                "Always return a detailed paragraph or bullets."
            )
        )
        return self.process_insights(state, system_message)

    def creation_operation(self, state: State) -> State:
        filtered_records = state.get("filtered_df", [])

        system_message = SystemMessage(
            content=(
                "You are a data analyst agent. You are given wallet creation records in "
                "tabular format. "
                "Your job is to create a comprehensive insight report, "
                "NOT just answer the user's question. "
                f"Answer question based on the data {filtered_records}"
                "Regardless of what the user asked earlier, you must include:\n\n"
                "1. Total number of wallets created\n"
                "2. Top users and location involved (if available). "
                "The location data can be fetched from "
                "location field.\n"
                "3. Wallet ID details\n"
                "4. Anomalies or suspicious activities\n"
                "5. Any recommendation for further analysis\n\n"
                "⚠️ Do NOT return just a single sentence or count. "
                "Always return a detailed paragraph or bullets."
            )
        )
        return self.process_insights(state, system_message)

    def transaction_operation(self, state: State) -> State:
        filtered_records = state.get("filtered_df", [])

        system_message = SystemMessage(
            content=(
                "You are a data analyst agent. You are given wallet transaction records in "
                "tabular format. "
                "Transaction operation is mixed of deposit, withdraw and transfer "
                "operations. "
                "Your job is to create a comprehensive insight report, "
                "NOT just answer the user's question. "
                f"Answer question based on the data {filtered_records}"
                "Regardless of what the user asked earlier, you must include:\n\n"
                "1. Total number of transactions happened which is aggregation of deposit, "
                "withdraw and transfer operations\n"
                "2. Highest transaction amount and the transaction type\n"
                "3. Currency involved in the transactions\n"
                "4. Anomalies or suspicious activities\n"
                "5. Any recommendation for further analysis\n\n"
                "⚠️ Do NOT return just a single sentence or count. "
                "Always return a detailed paragraph or bullets."
            )
        )
        return self.process_insights(state, system_message)

    def add_nodes_to_graph(self, graph_builder, state: State):
        self.logger.info(f"Tools registered: {self.tools}")
        graph_builder.add_node(
            "extract_parameters", self.extract_date_range_and_operation
        )
        graph_builder.add_node("query_data", self.query_wallet_data_from_loki)
        graph_builder.add_node("creation_operation", self.creation_operation)
        graph_builder.add_node("transfer_operation", self.transfer_operation)
        graph_builder.add_node("deposit_operation", self.deposit_operation)
        graph_builder.add_node("withdraw_operation", self.withdraw_operation)
        graph_builder.add_node("delete_operation", self.delete_operation)
        graph_builder.add_node("error_operation", self.error_operation)
        graph_builder.add_node("get_operation", self.get_operation)
        graph_builder.add_node("transaction_operation", self.transaction_operation)
        graph_builder.add_edge(START, "extract_parameters")
        graph_builder.add_edge("extract_parameters", "query_data")
        operation_node_map = {
            "creation": "creation_operation",
            "transfer": "transfer_operation",
            "deposit": "deposit_operation",
            "withdraw": "withdraw_operation",
            "delete": "delete_operation",
            "error": "error_operation",
            "get": "get_operation",
            "transaction": "transaction_operation",
        }

        graph_builder.add_conditional_edges(
            "query_data", self.safe_tools_condition, operation_node_map
        )
        for op_node in operation_node_map.values():
            graph_builder.add_edge(op_node, self.agent_node_name)

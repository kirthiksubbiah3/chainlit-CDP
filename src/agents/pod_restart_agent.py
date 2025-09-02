import subprocess
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START
from pydantic import BaseModel, Field

from config import app_config
from agents.base_agent import BaseAgent, BaseState

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass


class EKSPodRestartModel(BaseModel):
    cyberark_user_id: str = Field(
        description="Get the Cyberark user ID from the AI message"
    )
    cyberark_password: str = Field(
        description="Get the Cyberark password from the AI message"
    )
    aws_role_arn: str = Field(description="Get the aws_role_arn from the AI message")
    aws_profile: str = Field(description="Get the aws_profile from the AI message")
    cluster_name: str = Field(
        description="Get the kubernetes cluster_name from the AI message"
    )
    region: str = Field(description="Get the aws region from the AI message")
    namespace: str = Field(
        description="Get the kubernetes namespace from the AI message"
    )
    deployment: str = Field(
        description="Get the kubernetes deployment from the AI message"
    )


class State(BaseState):
    model: Optional[EKSPodRestartModel]


class PodRestartAgent(BaseAgent):
    def __init__(self):
        super().__init__(servers_to_use=[])
        self.state_schema = State
        self.model = EKSPodRestartModel

    def evaluator(self, state: State) -> State:
        self.logger.info("Calling the evaluator for all messages")

        combined_content = self._get_all_message_content(state)

        system_message = SystemMessage(
            content=(
                "You are an evaluator that extracts all required fields "
                "for restarting a pod in EKS. Use the entire conversation "
                "history to infer values."
            )
        )

        human_message = HumanMessage(
            content=f"""Please extract the details from the conversation history:
        Conversation:
        '''{combined_content}'''"""
        )

        evaluator_messages = [system_message, human_message]

        eval_result: EKSPodRestartModel = self.llm_structured_output.invoke(
            evaluator_messages
        )
        state["messages"].append(
            self._to_assistant_msg(f"Evaluator findings:{eval_result.model_dump()}")
        )
        state["model"] = self.model(
            **{
                "cyberark_user_id": eval_result.cyberark_user_id,
                "cyberark_password": eval_result.cyberark_password,
                "aws_role_arn": eval_result.aws_role_arn,
                "aws_profile": eval_result.aws_profile,
                "cluster_name": eval_result.cluster_name,
                "region": eval_result.region,
                "namespace": eval_result.namespace,
                "deployment": eval_result.deployment,
            }
        )
        return state

    def request_access(self, state: State):
        """
        Request heightened tier-one access via CyberArk/SNOW
        (In real flow, this would be an API call, but here we just log).
        """
        return {
            "messages": [
                self._to_assistant_msg(
                    f"Requested SNOW access for {state['model'].cyberark_user_id}"
                )
            ]
        }

    def setup_aws_cli(self, state: State):
        """
        Configure AWS CLI (assuming already installed in Anthem machine).
        """
        return {
            "messages": [
                self._to_assistant_msg(
                    f"AWS CLI configured for profile {state['model'].aws_profile}"
                )
            ]
        }

    def run_saml_api(self, state: State):
        """
        Use samlapi.py to login and fetch temporary creds.
        """
        # TODO Uncomment once the  samlapi.py file available
        # cmd = [
        #     "python", "samlapi.py",
        #     state["model"].cyberark_user_id, state["model"].cyberark_password,
        #     state["model"].aws_role_arn, state["model"].aws_profile
        # ]
        # subprocess.run(cmd, check=True)
        return {
            "messages": [
                self._to_assistant_msg(
                    f"SAML API run for role {state['model'].aws_profile}"
                )
            ]
        }

    def list_clusters(self, state: State):
        """
        List clusters in AWS account.
        """
        cmd = [
            "aws",
            "eks",
            "list-clusters",
            # "--profile", state["aws_profile"],# TODO uncomment if profile available
            "--region",
            state["model"].region,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {
            "messages": [self._to_assistant_msg(f"List clusters\n {result.stdout}")]
        }

    def update_kubeconfig(self, state: State):
        """
        Update kubeconfig to connect to required cluster.
        """
        cmd = [
            "aws",
            "eks",
            "--region",
            state["model"].region,
            "update-kubeconfig",
            "--name",
            state["model"].cluster_name,
            # "--profile", state["model"].aws_profile # TODO uncomment if profile available
        ]
        subprocess.run(cmd, check=True)
        return {
            "messages": [
                self._to_assistant_msg(
                    f"Kubeconfig updated for{state['model'].cluster_name}"
                )
            ]
        }

    def restart_deployment(self, state: State):
        """
        Restart deployment in given namespace.
        """
        cmd = [
            "kubectl",
            "rollout",
            "restart",
            f"deployment/{state['model'].deployment}",
            "-n",
            state["model"].namespace,
        ]
        subprocess.run(cmd, check=True)
        return {
            "messages": [
                self._to_assistant_msg(
                    f"Deployment {state['model'].deployment} restarted"
                )
            ]
        }

    def verify_pods(self, state: State):
        """
        Verify pods restarted.
        """
        cmd = ["kubectl", "get", "pods", "-n", state["model"].namespace]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {
            "messages": [self._to_assistant_msg(f"Verifying pods\n {result.stdout}")]
        }

    def verify_health_portal(self, state: State):
        """
        Login EHDS portal and check health (mocked).
        """
        return {
            "messages": [
                self._to_assistant_msg(
                    f"Health check verified in EHDS portal for{state['model'].cluster_name}"
                )
            ]
        }

    def add_nodes_to_graph(self, graph_builder, state):
        graph_builder.add_node("evaluator", self.evaluator)
        graph_builder.add_node("request_access", self.request_access)
        graph_builder.add_node("setup_aws_cli", self.setup_aws_cli)
        graph_builder.add_node("run_saml_api", self.run_saml_api)
        graph_builder.add_node("list_clusters", self.list_clusters)
        graph_builder.add_node("update_kubeconfig", self.update_kubeconfig)
        graph_builder.add_node("restart_deployment", self.restart_deployment)
        graph_builder.add_node("verify_pods", self.verify_pods)
        graph_builder.add_node("verify_health_portal", self.verify_health_portal)

        # Transitions
        graph_builder.add_edge(START, "evaluator")
        graph_builder.add_edge("evaluator", "request_access")
        graph_builder.add_edge("request_access", "setup_aws_cli")
        graph_builder.add_edge("setup_aws_cli", "run_saml_api")
        graph_builder.add_edge("run_saml_api", "list_clusters")
        graph_builder.add_edge("list_clusters", "update_kubeconfig")
        graph_builder.add_edge("update_kubeconfig", "restart_deployment")
        graph_builder.add_edge("restart_deployment", "verify_pods")
        graph_builder.add_edge("verify_pods", "verify_health_portal")
        graph_builder.add_edge("verify_health_portal", self.agent_node_name)

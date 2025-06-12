from langchain_aws import ChatBedrockConverse


class bedrock:
    def __init__(self, model_name: str, region: str = "us-east-1"):
        self.model_name = model_name
        self.region = region

    def get_model_details(self):
        model_details = ChatBedrockConverse(model=self.model_name, max_tokens=1500)

        return model_details

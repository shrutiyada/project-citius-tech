from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatPromptExecutionSettings

class ChatAgent:
    def __init__(self, endpoint: str, api_key: str, deployment_name: str, api_version: str = "2024-02-15-preview"):
        print(f"[SEMANTIC KERNEL] Initializing Chat Agent with Azure OpenAI deployment '{deployment_name}'...")
        self.kernel = Kernel()
        chat_service = AzureChatCompletion(
            deployment_name=deployment_name,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.kernel.add_service(chat_service)
        
        self.system_message = (
            "You are a helpful Medical Assistant. "
            "Use the provided 'Patient Data' and 'Policy Data' to answer the user's question accurately. "
            "If the answer is not contained within the provided data, state that you do not have enough information."
        )
        
        self.execution_settings = OpenAIChatPromptExecutionSettings(
            temperature=0.3,
        )

    async def answer_question(self, query: str, patient_data: str, policy_data: str) -> str:
        prompt = (
            f"{self.system_message}\n\n"
            f"--- Patient Data Context ---\n{patient_data}\n\n"
            f"--- Policy Data Context ---\n{policy_data}\n\n"
            f"User Question: {query}"
        )
        
        try:
            result = await self.kernel.invoke_prompt(
                prompt=prompt,
                plugin_name="ChatBot",
                function_name="AnswerQuery",
                settings=self.execution_settings
            )
            return str(result)
        except Exception as e:
            print(f"[CHAT AGENT ERROR] {e}")
            return "An error occurred while generating the response."

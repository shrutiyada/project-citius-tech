import os
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import DefaultAzureCredential

class ChatAgent:
    def __init__(self, endpoint: str, api_key: str = None, deployment_name: str = "gpt-4o", api_version: str = "2024-02-15-preview"):
        print(f"[MAF] Initializing Chat Agent with Azure OpenAI deployment '{deployment_name}'...")
        
        self.credential = DefaultAzureCredential()
        self.client = FoundryChatClient(
            endpoint=endpoint,
            credential=self.credential,
            deployment_name=deployment_name,
            api_version=api_version
        )
        
        self.system_message = (
            "You are a helpful Medical Assistant. "
            "Use the provided 'Patient Data' and 'Policy Data' to answer the user's question accurately. "
            "If the answer is not contained within the provided data, state that you do not have enough information.\n\n"
            "⚠️ CRITICAL SAFETY WARNING ON CITATIONS ⚠️\n"
            "When answering questions, you MUST cite the exact [Page X] from the context data for every claim you make.\n"
            "DO NOT guess or invent page numbers. You must locate the exact [Page X] marker that immediately precedes the text you are quoting.\n"
            "Failure to provide accurate citations is a critical safety violation."
        )
        
        self.agent = Agent(
            client=self.client,
            system_message=self.system_message
        )

    async def answer_question(self, query: str, patient_data: str, policy_data: str) -> str:
        prompt = (
            f"--- Patient Data Context ---\n{patient_data}\n\n"
            f"--- Policy Data Context ---\n{policy_data}\n\n"
            f"User Question: {query}"
        )
        
        try:
            result = await self.agent.run(prompt)
            return str(result)
        except Exception as e:
            print(f"[MAF ERROR] {e}")
            return "An error occurred while generating the response."

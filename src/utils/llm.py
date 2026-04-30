from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import os
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self):
        self.model = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "gpt-4o"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_BASE"),
            temperature=0.7
        )
        self.json_parser = JsonOutputParser()

    async def get_json_response(self, prompt_template: str, input_variables: dict):
        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.model | self.json_parser
        return await chain.ainvoke(input_variables)

    async def get_text_response(self, prompt_template: str, input_variables: dict):
        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.model
        response = await chain.ainvoke(input_variables)
        return response.content

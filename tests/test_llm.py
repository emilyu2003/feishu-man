import asyncio
import os
from dotenv import load_dotenv
from src.utils.llm import LLMService

async def test_doubao():
    load_dotenv()
    print("Testing Doubao 2.0 Pro connection...")
    print(f"Base URL: {os.getenv('OPENAI_API_BASE')}")
    print(f"Model: {os.getenv('MODEL_NAME')}")
    
    llm = LLMService()
    try:
        response = await llm.get_text_response("你好，请简短介绍一下你自己。", {})
        print("\nResponse from Doubao:")
        print("-" * 30)
        # 尝试使用 utf-8 编码输出以避免 Windows 终端编码问题
        print(response.encode('utf-8', errors='ignore').decode('utf-8'))
        print("-" * 30)
        print("\nConnection successful!")
    except Exception as e:
        print(f"\nConnection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_doubao())

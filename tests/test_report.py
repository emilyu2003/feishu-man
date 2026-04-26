
import asyncio
import os
from src.utils.feishu_client import FeishuClient
from dotenv import load_dotenv

async def test_report():
    load_dotenv()
    client = FeishuClient(
        os.getenv("FEISHU_APP_ID"),
        os.getenv("FEISHU_APP_SECRET"),
        os.getenv("FEISHU_BASE_ID")
    )
    
    table_id = await client.get_table_id_by_name("招聘数据分析")
    print(f"Table ID: {table_id}")
    
    if table_id:
        try:
            res = await client.add_record(table_id, {
                "报告类型": "Test Report",
                "报告内容": "Short content",
                "生成时间": "2026-04-25 12:00:00"
            })
            print(f"Record added: {res}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_report())

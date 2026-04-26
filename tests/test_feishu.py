import asyncio
import os
from src.utils.feishu_client import FeishuClient
from dotenv import load_dotenv

async def test_connection():
    load_dotenv()
    feishu = FeishuClient(
        app_id=os.getenv("FEISHU_APP_ID"),
        app_secret=os.getenv("FEISHU_APP_SECRET"),
        base_id=os.getenv("FEISHU_BASE_ID")
    )
    
    print(f"Testing connection with Base ID: {feishu.base_id}")
    try:
        table_id = await feishu.get_table_id_by_name("岗位描述")
        if table_id:
            print(f"Successfully connected! Found table '岗位描述' with ID: {table_id}")
        else:
            print("Connected, but table '岗位描述' not found. This is expected in a new base.")
            # Try to list tables to see if the Base ID is valid
            args = ["base", "+table-list", "--base-token", feishu.base_id, "--as", "bot"]
            res = feishu._run_cli(args)
            print(f"Raw Table List Result: {res}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())

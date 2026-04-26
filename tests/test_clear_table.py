import asyncio
import os
from dotenv import load_dotenv
from src.utils.feishu_client import FeishuClient

async def test_clear_all_tables():
    load_dotenv()
    
    # 初始化飞书客户端
    feishu = FeishuClient(
        app_id=os.getenv("FEISHU_APP_ID"),
        app_secret=os.getenv("FEISHU_APP_SECRET"),
        base_id=os.getenv("FEISHU_BASE_ID")
    )
    
    print("=== 测试清空所有飞书表格 ===")
    
    # 定义所有表格名称
    table_names = [
        "岗位描述",
        "简历池", 
        "面试官可用时间",
        "面试邀约记录",
        "面试安排",
        "招聘数据分析"
    ]
    
    for table_name in table_names:
        print(f"\n处理表格: {table_name}")
        
        # 获取表格ID
        table_id = await feishu.get_table_id_by_name(table_name)
        if not table_id:
            print(f"表格 {table_name} 不存在，跳过")
            continue
            
        print(f"表格ID: {table_id}")
        
        # 清空表格
        await feishu.clear_table(table_id)
        
        # 验证清空结果
        remaining_records = await feishu.list_records(table_id)
        if len(remaining_records) == 0:
            print(f"[OK] 表格 {table_name} 清空成功！")
        else:
            print(f"[ERROR] 表格 {table_name} 清空失败，剩余 {len(remaining_records)} 条记录:")
            for rec in remaining_records:
                print(f"  - {rec}")
    
    print("\n=== 所有表格处理完成 ===")

if __name__ == "__main__":
    asyncio.run(test_clear_all_tables())
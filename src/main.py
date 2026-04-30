import asyncio
import os
from dotenv import load_dotenv
from src.utils.feishu_client import FeishuClient
from src.utils.llm import LLMService
from src.core.graph import RecruitmentWorkflow
from src.core.state import RecruitmentState

async def main():
    load_dotenv()
    
    # 初始化组件
    feishu = FeishuClient(
        app_id=os.getenv("FEISHU_APP_ID"),
        app_secret=os.getenv("FEISHU_APP_SECRET"),
        base_id=os.getenv("FEISHU_BASE_ID")
    )
    llm = LLMService()
    
    # 初始化工作流
    workflow = RecruitmentWorkflow(feishu, llm)
    
    # 招聘目标：需要n个候选人接受Offer
    target_accepted = int(os.getenv("NUM_CANDIDATES", 2))
    accepted_count = 0
    batch_num = 1
    
    print(f"=== 招聘系统启动，目标录用人数: {target_accepted} ===")
    
    # 初始状态（仅在第一次创建）
    current_state: RecruitmentState = {
        "jd": os.getenv("JD_CONTENT", "Python Developer"),
        "num_candidates_to_generate": min(target_accepted - accepted_count, 3),
        "table_ids": {},
        "resumes": [],
        "slots": [],
        "interviews": [],
        "invitations": [],
        "current_step": "init",
        "logs": [],
        "is_finished": False,
        "initialized": False,           # 首次运行时清空表格
        "target_candidate_ids": [],
        "pending_offer_candidates": []
    }
    
    while accepted_count < target_accepted:
        print(f"\n\n=== 第 {batch_num} 批招聘开始 ===")
        
        # 更新当前批次需要生成的候选人数量
        current_state["num_candidates_to_generate"] = min(target_accepted - accepted_count, 3)
        
        # 运行工作流（使用当前状态）
        final_state = None
        async for event in workflow.app.astream(current_state):
            for node_name, state_update in event.items():
                print(f"Finished node: {node_name}")
                final_state = state_update
        
        # 更新状态为最终状态（跨批次保持）
        if final_state:
            current_state = final_state
        
        # 统计本批次接受Offer的人数
        if final_state and "resumes" in final_state:
            batch_accepted = sum(1 for r in final_state["resumes"] if r.get("Offer状态") == "已接受")
            accepted_count += batch_accepted
            print(f"\n第 {batch_num} 批招聘结束，本批次录用: {batch_accepted} 人，累计录用: {accepted_count}/{target_accepted} 人")
        
        batch_num += 1
        
        # 检查是否达到目标
        if accepted_count >= target_accepted:
            break
            
        # 如果还有剩余名额，继续下一批招聘
        print(f"继续生成下一批候选人...")
        
    print(f"\n=== 招聘完成！共录用 {accepted_count} 名候选人，达到目标要求 ===")

if __name__ == "__main__":
    asyncio.run(main())

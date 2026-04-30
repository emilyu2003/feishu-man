import asyncio
import os
from dotenv import load_dotenv
from src.utils.feishu_client import FeishuClient
from src.utils.llm import LLMService
from src.core.graph import RecruitmentWorkflow
from src.core.state import RecruitmentState
from datetime import datetime, timedelta

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
    target_accepted = int(os.getenv("NUM_CANDIDATES", 3))
    accepted_count = 0
    batch_num = 1
    # 记录下一批次的起始时间，确保时间不会重叠
    next_batch_start_date = datetime.now() + timedelta(days=1)  # 第一批次从明天开始
    # 初始化标记：仅第一次运行时清空表格并创建结构
    initialized = False
    
    print(f"=== 招聘系统启动，目标录用人数: {target_accepted} ===")
    
    while accepted_count < target_accepted:
        print(f"\n\n=== 第 {batch_num} 批招聘开始 ===")
        
        # 初始状态
        initial_state: RecruitmentState = {
            "jd": os.getenv("JD_CONTENT", "Python Developer"),
            "num_candidates_to_generate": min(target_accepted - accepted_count, 3),  # 每批最多生成3个候选人
            "table_ids": {},
            "resumes": [],
            "slots": [],
            "interviews": [],
            "invitations": [],
            "current_step": "init",
            "logs": [],
            "is_finished": False,
            "target_candidate_ids": [],
            "pending_offer_candidates": [],
            "start_date": next_batch_start_date.strftime("%Y-%m-%d"),  # 传递给工作流的起始日期
            "initialized": initialized  # 初始化标记
        }
        
        # 运行工作流
        final_state = None
        async for event in workflow.app.astream(initial_state):
            for node_name, state_update in event.items():
                print(f"Finished node: {node_name}")
                final_state = state_update
                
        # 第一次运行完成后，标记为已初始化，后续批次不再清空表格
        if not initialized:
            initialized = True
            
        # 统计本批次接受Offer的人数
        batch_accepted = 0
        if final_state and "resumes" in final_state:
            batch_accepted = sum(1 for r in final_state["resumes"] if r.get("Offer状态") == "已接受")
            accepted_count += batch_accepted
            print(f"\n第 {batch_num} 批招聘结束，本批次录用: {batch_accepted} 人，累计录用: {accepted_count}/{target_accepted} 人")
            
        batch_num += 1
        
        # 检查是否达到目标
        if accepted_count >= target_accepted:
            break
            
        # 下一批次时间从当前批次的最晚面试时间+1天开始
        if final_state and "slots" in final_state and final_state["slots"]:
            # 找到本批次的最晚面试日期
            slot_dates = []
            for slot in final_state["slots"]:
                try:
                    slot_date = datetime.strptime(slot["日期"], "%Y-%m-%d")
                    slot_dates.append(slot_date)
                except:
                    pass
            if slot_dates:
                max_date = max(slot_dates)
                next_batch_start_date = max_date + timedelta(days=1)
            else:
                next_batch_start_date += timedelta(days=7)
        else:
            # 如果没有slot数据，默认向后推7天
            next_batch_start_date += timedelta(days=7)
            
        # 如果还有剩余名额，继续下一批招聘
        print(f"下一批次招聘将从 {next_batch_start_date.strftime('%Y-%m-%d')} 开始...")
        
    print(f"\n=== 招聘完成！共录用 {accepted_count} 名候选人，达到目标要求 ===")

if __name__ == "__main__":
    asyncio.run(main())

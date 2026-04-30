from typing import TypedDict, List, Dict, Any, Optional

class RecruitmentState(TypedDict):
    # 基础配置
    jd: str
    num_candidates_to_generate: int
    start_date: str  # 批次起始日期，格式YYYY-MM-DD
    
    # 飞书 Table IDs
    table_ids: Dict[str, str]
    
    # 实体数据
    resumes: List[Dict[str, Any]]        # 简历池数据
    slots: List[Dict[str, Any]]          # 面试官可用时间槽
    interviews: List[Dict[str, Any]]     # 面试安排记录
    invitations: List[Dict[str, Any]]    # 面试邀约记录
    
    # 流程控制
    current_step: str 
    logs: List[str]
    is_finished: bool
    initialized: bool  # 是否已经初始化过表格，避免每批次重复清空
    
    # 临时变量（用于节点间传递）
    target_candidate_ids: List[str]      # 当前轮次处理的候选人
    pending_offer_candidates: List[str]  # 待决定 Offer 的候选人

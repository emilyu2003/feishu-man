from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class ScreeningStatus(str, Enum):
    PENDING = "待筛选"
    SCREENED = "已筛选"
    PASS = "通过"
    FAIL = "不通过"

class InterviewStatus(str, Enum):
    PENDING = "待面试"
    ONGOING = "进行中"
    COMPLETED = "已完成"
    PASS = "通过"
    FAIL = "不通过"

class OfferStatus(str, Enum):
    PENDING = "待发放"
    SENT = "已发放"
    ACCEPTED = "已接受"
    REJECTED = "已拒绝"

class Resume(BaseModel):
    record_id: Optional[str] = None
    candidate_id: str = Field(..., alias="候选人ID")
    name: str = Field(..., alias="姓名")
    gender: str = Field(..., alias="性别")
    age: int = Field(..., alias="年龄")
    education: str = Field(..., alias="学历")
    experience: str = Field(..., alias="工作经验")
    skills: str = Field(..., alias="技能标签")
    content: str = Field(..., alias="简历内容")
    screening_status: ScreeningStatus = Field(ScreeningStatus.PENDING, alias="筛选状态")
    similarity_score: Optional[float] = Field(0.0, alias="相似度评分")
    interview_status: InterviewStatus = Field(InterviewStatus.PENDING, alias="面试状态")
    offer_status: OfferStatus = Field(OfferStatus.PENDING, alias="Offer状态")

class InterviewSlot(BaseModel):
    record_id: Optional[str] = None
    interviewer_id: str = Field(..., alias="面试官ID")
    date: str = Field(..., alias="日期")
    slot: str = Field(..., alias="时段") # 上午/下午/晚上
    specific_time: str = Field(..., alias="具体时间")
    status: str = Field("可用", alias="可用状态") # 可用/已占用

class InterviewRecord(BaseModel):
    record_id: Optional[str] = None
    interview_id: str = Field(..., alias="面试ID")
    candidate_id: str = Field(..., alias="候选人ID")
    interviewer_id: str = Field(..., alias="面试官ID")
    start_time: str = Field(..., alias="面试时间")
    status: InterviewStatus = Field(InterviewStatus.PENDING, alias="面试状态")
    feedback: Optional[str] = Field("", alias="面试反馈")
    score: Optional[float] = Field(0.0, alias="评估结果")
    arrangement_status: str = Field("待确认", alias="安排状态")

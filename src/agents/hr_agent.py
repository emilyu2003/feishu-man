from ..utils.llm import LLMService
from ..schema.models import ScreeningStatus, InterviewStatus, OfferStatus
import json

class HRAgent:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def screen_resume(self, jd: str, resume_content: str) -> dict:
        """简历筛选：打分并给出结论"""
        prompt = """
        你是一名资深 HR。请根据岗位描述 (JD) 对候选人的简历进行评分和筛选。
        JD 内容: {jd}
        候选人简历: {resume}
        
        请输出 JSON 格式:
        - score: 0-100 的匹配度评分 (float)
        - conclusion: "通过" 或 "不通过"
        - reason: 简短的理由 (50字以内)
        """
        result = await self.llm.get_json_response(prompt, {"jd": jd, "resume": resume_content})
        
        # 映射状态
        status = ScreeningStatus.PASS if result["conclusion"] == "通过" else ScreeningStatus.FAIL
        return {
            "score": result["score"],
            "status": status.value,
            "reason": result["reason"]
        }

    async def make_final_decision(self, interview_feedback: str) -> str:
        """根据面试反馈做最终决定"""
        if "评估结果: 通过" in interview_feedback:
            return OfferStatus.SENT.value
        else:
            return OfferStatus.REJECTED.value

    async def generate_report(self, all_data: list) -> str:
        """生成招聘分析报告"""
        prompt = """
        你是一个招聘数据分析专家。请根据以下招聘全流程数据，生成一份结构化的招聘分析报告。
        数据: {data}
        
        报告应包含:
        1. 招聘漏斗统计 (简历数 -> 筛选通过数 -> 面试数 -> Offer数)
        2. 候选人质量分析
        3. 招聘效率与建议
        """
        report = await self.llm.get_text_response(prompt, {"data": json.dumps(all_data, ensure_ascii=False)})
        return report

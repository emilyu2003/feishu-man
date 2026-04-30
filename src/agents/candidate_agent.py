from ..utils.llm import LLMService
from ..schema.models import Resume, ScreeningStatus, InterviewStatus, OfferStatus
import uuid
import random

class CandidateAgent:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def generate_resume(self, jd: str) -> dict:
        """根据 JD 随机生成简历"""
        prompt = """
        你是一个求职者，正在根据以下岗位描述 (JD) 生成一份虚构的简历。
        JD 内容: {jd}
        
        请生成一个 JSON 格式的简历，包含以下字段:
        - 姓名: 随机中文名
        - 性别: 男/女
        - 年龄: 22-35 之间的整数
        - 学历: [985院校, 211院校, 普通本科, 硕士, 博士] 之一
        - 工作经验: 1-10 年之间的描述
        - 技能标签: 与 JD 相关的 0-5 个关键词，用逗号分隔
        - 简历内容: 一段 200 字左右的自我介绍和经历描述，体现与 JD 的匹配度。
        
        重要要求：请随机生成匹配度不同的简历，30%概率生成与 JD 匹配度低的简历（技能标签少、经验不相关），70%概率生成匹配度中高的简历。
        输出格式必须为 JSON。
        """
        resume_data = await self.llm.get_json_response(prompt, {"jd": jd})
        
        # 补全业务字段
        resume_data["候选人ID"] = f"CAND_{uuid.uuid4().hex[:8]}"
        resume_data["筛选状态"] = ScreeningStatus.PENDING.value
        resume_data["相似度评分"] = 0.0
        resume_data["面试状态"] = InterviewStatus.PENDING.value
        resume_data["Offer状态"] = OfferStatus.PENDING.value
        
        return resume_data

    async def answer_question(self, resume: dict, question: str, question_type: str = "") -> str:
        """回答面试官的问题
        :param resume: 候选人简历信息
        :param question: 面试官的问题
        :param question_type: 问题类型（可选）
        :return: 回答内容
        """
        prompt = f"""
        你是求职者 {resume['姓名']}，正在参加面试。请根据你的简历信息回答面试官的问题。
        
        简历信息：
        - 姓名：{resume['姓名']}
        - 学历：{resume['学历']}
        - 工作经验：{resume['工作经验']}
        - 技能标签：{resume['技能标签']}
        - 简历内容：{resume['简历内容']}
        
        面试官问题：{question}
        
        请用自然、专业的语言回答这个问题，体现你的能力和经验。
        
        请严格按照JSON格式返回结果，必须包含一个answer字段，值为你的回答内容。
        输出示例：{"answer": "你的回答内容"}
        """
        
        if question_type:
            prompt += f"\n问题类型：{question_type}"
        
        response = await self.llm.get_json_response(prompt, {})
        return response.get("answer", "")

    async def decide_interview(self, interview_info: dict) -> int:
        """选择面试时间段 (Flow 5 step 7)
        返回值：
        - >=0: 选择对应的时间段索引
        - -1: 所有时间段都不满意，需要重新安排
        """
        available_slots = interview_info.get("available_slots", [])
        if not available_slots:
            return -1
            
        # 模拟决策逻辑：80%概率选择一个时间段，20%概率都不满意
        if random.random() < 0.8:
            # 随机选择一个时间段
            selected_idx = random.randint(0, len(available_slots)-1)
            selected_time = f"{available_slots[selected_idx]['日期']} {available_slots[selected_idx]['具体时间']}"
            print(f"Candidate {interview_info.get('候选人ID')} 选择了面试时间段: {selected_time}")
            return selected_idx
        else:
            print(f"Candidate {interview_info.get('候选人ID')} 对所有时间段都不满意，需要重新安排")
            return -1
            
    async def answer_questions(self, questions: list) -> list:
        """回答选择题（随机选择答案，不需要调用大模型，快速完成）"""
        answers = []
        options = ["A", "B", "C", "D"]
        for q in questions:
            # 随机选择一个答案
            answers.append(random.choice(options))
        return answers

    async def decide_offer(self, offer_info: dict) -> str:
        """决定是否接受 Offer (Flow 7 step 5)"""
        # 模拟决策逻辑：80% 概率接受
        decision = OfferStatus.ACCEPTED.value if random.random() < 0.8 else OfferStatus.REJECTED.value
        print(f"Candidate {offer_info.get('候选人ID')} {'接受' if decision == OfferStatus.ACCEPTED.value else '拒绝'} 了 Offer")
        return decision

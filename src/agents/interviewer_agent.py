from ..utils.llm import LLMService
from ..schema.models import InterviewStatus
from ..agents.candidate_agent import CandidateAgent
import random
from datetime import datetime, timedelta
import json

class InterviewerAgent:
    def __init__(self, llm_service: LLMService, interviewer_id: str = "INTERVIEWER_01"):
        self.llm = llm_service
        self.interviewer_id = interviewer_id

    async def set_availability(self) -> list:
        """设置未来 3 天的可用时间槽 (Flow 3)"""
        slots = []
        # 每天最多上午（10:00-12:00）、下午（14:00-17:00）、晚上（19:00-21:00）
        # 简化逻辑：每个时段随机生成 1-2 个整点或半点的时间槽
        time_configs = [
            ("上午", ["10:00", "10:30", "11:00", "11:30"]),
            ("下午", ["14:00", "14:30", "15:00", "15:30", "16:00", "16:30"]),
            ("晚上", ["19:00", "19:30", "20:00", "20:30"])
        ]
        
        # 生成未来 7 天的可用时间槽，每天随机选择 1 个时段，符合设计文档"最长预约一周内的面试"要求
        for day_offset in range(7):
            current_date = (datetime.now() + timedelta(days=day_offset + 1)).strftime("%Y-%m-%d")
            # 随机选择 1 个时段
            selected_periods = random.sample(time_configs, k=1)
            
            for period, times in selected_periods:
                # 每个时段至少一个可用
                selected_times = random.sample(times, k=random.randint(1, 2))
                for t in selected_times:
                    slots.append({
                        "面试官ID": self.interviewer_id,
                        "日期": current_date,
                        "时段": period,
                        "具体时间": t,
                        "可用状态": "可用"
                    })
                    
        return slots

    async def conduct_interview(self, jd: str, resume: dict, candidate: CandidateAgent) -> dict:
        """进行交互式面试 (Flow 6)"""
        interview_rounds = []
        
        # 阶段一：自我介绍与背景了解（1-2轮）
        intro_rounds = await self._phase1_introduction(resume, candidate)
        interview_rounds.extend(intro_rounds)
        
        # 阶段二：技术能力考察（3-5轮）
        tech_rounds = await self._phase2_technical(jd, resume, candidate)
        interview_rounds.extend(tech_rounds)
        
        # 阶段三：项目经验与团队协作（2-3轮）
        project_rounds = await self._phase3_project(resume, candidate)
        interview_rounds.extend(project_rounds)
        
        # 计算各维度得分
        scores = self._calculate_scores(interview_rounds)
        total_score = sum(scores.values())
        
        # 判定是否通过
        passed = total_score >= 60
        
        # 生成面试官评语
        feedback = await self._generate_feedback(scores, total_score, passed)
        
        return {
            "interview_rounds": interview_rounds,
            "scores": scores,
            "total_score": total_score,
            "passed": passed,
            "feedback": feedback
        }

    async def _phase1_introduction(self, resume: dict, candidate: CandidateAgent) -> list:
        """阶段一：自我介绍与背景了解（1-2轮）"""
        rounds = []
        num_rounds = random.randint(1, 2)
        
        for i in range(num_rounds):
            if i == 0:
                question = f"请{resume['姓名']}做一下自我介绍"
            else:
                question = "请介绍一下你的工作经历和主要技能"
            
            # 调用候选人Agent回答问题
            answer = await candidate.answer_question(resume, question)
            
            rounds.append({
                "phase": "自我介绍与背景了解",
                "question": question,
                "answer": answer,
                "evaluation_dimension": ["沟通能力", "表达能力"]
            })
        
        return rounds

    async def _phase2_technical(self, jd: str, resume: dict, candidate: CandidateAgent) -> list:
        """阶段二：技术能力考察（3-5轮）"""
        rounds = []
        num_rounds = random.randint(3, 5)
        
        prompt = f"""
        你是一个专业面试官，请根据以下岗位描述 (JD) 生成 {num_rounds} 个技术问题。
        JD 内容: {jd}
        候选人简历: {resume['简历内容']}
        技能标签: {resume['技能标签']}
        
        每个问题必须包含:
        - question: 问题内容
        - question_type: 问题类型（概念理解/实际应用/问题解决）
        - difficulty: 问题难度（基础/中等/困难）
        
        输出格式必须为 JSON 列表。
        """
        
        questions = await self.llm.get_json_response(prompt, {})
        
        for q in questions:
            # 调用候选人Agent回答问题
            answer = await candidate.answer_question(resume, q['question'], q['question_type'])
            
            rounds.append({
                "phase": "技术能力考察",
                "question": q['question'],
                "question_type": q['question_type'],
                "difficulty": q['difficulty'],
                "answer": answer,
                "evaluation_dimension": ["技术能力", "问题解决能力"]
            })
        
        return rounds

    async def _phase3_project(self, resume: dict, candidate: CandidateAgent) -> list:
        """阶段三：项目经验与团队协作（2-3轮）"""
        rounds = []
        num_rounds = random.randint(2, 3)
        
        prompt = f"""
        你是一个专业面试官，请根据以下候选人简历生成 {num_rounds} 个关于项目经验的深入问题。
        候选人简历: {resume['简历内容']}
        工作经验: {resume['工作经验']}
        
        每个问题必须包含:
        - question: 问题内容
        - focus: 关注点（项目细节/贡献/团队协作）
        
        输出格式必须为 JSON 列表。
        """
        
        questions = await self.llm.get_json_response(prompt, {})
        
        for q in questions:
            # 调用候选人Agent回答问题
            answer = await candidate.answer_question(resume, q['question'], q['focus'])
            
            rounds.append({
                "phase": "项目经验与团队协作",
                "question": q['question'],
                "focus": q['focus'],
                "answer": answer,
                "evaluation_dimension": ["项目经验", "团队协作"]
            })
        
        return rounds

    def _calculate_scores(self, interview_rounds: list) -> dict:
        """计算各维度得分"""
        scores = {
            "技术能力": 0,
            "项目经验": 0,
            "沟通能力": 0,
            "问题解决能力": 0,
            "团队协作": 0
        }
        
        # 根据回答质量随机评分（实际应用中应该由LLM评估）
        for round_data in interview_rounds:
            dimensions = round_data.get("evaluation_dimension", [])
            # 模拟评分：基于回答长度和内容质量
            answer_length = len(round_data.get("answer", ""))
            base_score = min(answer_length / 50, 10)  # 基础分
            
            for dim in dimensions:
                if dim in scores:
                    # 随机波动，模拟真实评估
                    random_factor = random.uniform(0.8, 1.2)
                    scores[dim] += base_score * random_factor
        
        # 归一化到各维度满分
        max_scores = {
            "技术能力": 30,
            "项目经验": 25,
            "沟通能力": 20,
            "问题解决能力": 15,
            "团队协作": 10
        }
        
        for dim in scores:
            scores[dim] = min(int(scores[dim]), max_scores[dim])
        
        return scores

    async def _generate_feedback(self, scores: dict, total_score: int, passed: bool) -> str:
        """生成面试官评语"""
        prompt = f"""
        你是一个专业面试官，请根据以下面试评分生成评语。
        
        各维度得分：
        - 技术能力：{scores['技术能力']}/30
        - 项目经验：{scores['项目经验']}/25
        - 沟通能力：{scores['沟通能力']}/20
        - 问题解决能力：{scores['问题解决能力']}/15
        - 团队协作：{scores['团队协作']}/10
        
        总分：{total_score}/100
        面试结果：{'通过' if passed else '不通过'}
        
        请生成一段简洁的评语（100字以内），总结候选人的表现。
        输出格式必须为 JSON，包含：
        - feedback: 评语内容
        """
        
        response = await self.llm.get_json_response(prompt, {})
        return response.get("feedback", "")

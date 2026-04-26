from ..utils.llm import LLMService
from ..schema.models import InterviewStatus
import random
from datetime import datetime, timedelta

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

    async def generate_questions(self, jd: str, num_questions: int = 10) -> list:
        """基于 JD 生成选择题"""
        prompt = """
        你是一个专业面试官，请根据以下岗位描述 (JD) 生成 {num} 道专业选择题。
        JD 内容: {jd}
        
        每道题必须包含:
        - id: 题目编号
        - question: 题干
        - options: {{'A': '...', 'B': '...', 'C': '...', 'D': '...'}}
        - answer: 正确选项 (A/B/C/D)
        
        输出格式必须为 JSON 列表。
        """
        questions = await self.llm.get_json_response(prompt, {"jd": jd, "num": num_questions})
        return questions

    def evaluate_performance(self, questions: list, candidate_answers: list) -> dict:
        """评分逻辑：正确率 > 25% 通过"""
        correct_count = 0
        total = len(questions)
        
        # 建立题目答案映射
        answer_key = {str(q['id']): q['answer'] for q in questions}
        
        details = []
        for ans in candidate_answers:
            q_id = str(ans['question_id'])
            is_correct = ans['answer'] == answer_key.get(q_id)
            if is_correct:
                correct_count += 1
            details.append({
                "question_id": q_id,
                "candidate_answer": ans['answer'],
                "correct_answer": answer_key.get(q_id),
                "is_correct": is_correct
            })
            
        accuracy = correct_count / total if total > 0 else 0
        passed = accuracy > 0.25
        
        return {
            "accuracy": accuracy,
            "passed": passed,
            "score": accuracy * 100,
            "feedback": f"共 {total} 题，答对 {correct_count} 题，正确率 {accuracy:.2%}。评估结果: {'通过' if passed else '不通过'}",
            "details": details
        }

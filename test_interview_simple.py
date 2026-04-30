import asyncio
import os
import sys

os.chdir('d:/miao/opencode/feishu-man')
sys.path.append('d:/miao/opencode/feishu-man')

from dotenv import load_dotenv
load_dotenv()

from src.agents.interviewer_agent import InterviewerAgent
from src.utils.llm import LLMService

async def test():
    print("测试交互式面试...")
    print("-" * 50)

    llm = LLMService()
    interviewer = InterviewerAgent(llm)

    resume = {
        "姓名": "张三",
        "学历": "985院校硕士",
        "工作经验": "5年Python后端",
        "技能标签": "Python, FastAPI, PostgreSQL",
        "简历内容": "有5年Python开发经验，熟悉FastAPI框架。"
    }

    jd = "招聘Python后端工程师，熟悉FastAPI和PostgreSQL"

    result = await interviewer.conduct_interview(jd, resume)

    print(f"\n总分: {result['total_score']}/100")
    print(f"通过: {'是' if result['passed'] else '否'}")
    print(f"评语: {result['feedback']}")
    print("\n各维度得分:")
    for k, v in result['scores'].items():
        print(f"  {k}: {v}")
    print(f"\n面试轮数: {len(result['interview_rounds'])}")
    print("-" * 50)

asyncio.run(test())
from langgraph.graph import StateGraph, END
from .state import RecruitmentState
from ..agents.hr_agent import HRAgent
from ..agents.interviewer_agent import InterviewerAgent
from ..agents.candidate_agent import CandidateAgent
from ..utils.feishu_client import FeishuClient
from ..utils.llm import LLMService
from ..schema.models import OfferStatus
import os
from datetime import datetime

class RecruitmentWorkflow:
    def __init__(self, feishu: FeishuClient, llm: LLMService):
        self.feishu = feishu
        self.llm = llm
        self.hr = HRAgent(llm)
        self.interviewer = InterviewerAgent(llm)
        self.candidate = CandidateAgent(llm)
        
        # 定义图
        workflow = StateGraph(RecruitmentState)
        
        # 添加节点
        workflow.add_node("initialize", self.node_initialize)
        workflow.add_node("generate_candidates", self.node_generate_candidates)
        workflow.add_node("set_availability", self.node_set_availability)
        workflow.add_node("screening", self.node_screening)
        workflow.add_node("scheduling", self.node_scheduling)
        workflow.add_node("confirm_interview", self.node_confirm_interview)
        workflow.add_node("interviewing", self.node_interviewing)
        workflow.add_node("offer_decision", self.node_offer_decision)
        workflow.add_node("reporting", self.node_reporting)
        
        # 设置边
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "generate_candidates")
        workflow.add_edge("generate_candidates", "set_availability")
        workflow.add_edge("set_availability", "screening")
        workflow.add_edge("screening", "scheduling")
        workflow.add_edge("scheduling", "confirm_interview")
        workflow.add_edge("confirm_interview", "interviewing")
        workflow.add_edge("interviewing", "offer_decision")
        workflow.add_edge("offer_decision", "reporting")
        workflow.add_edge("reporting", END)
        
        self.app = workflow.compile()

    async def node_initialize(self, state: RecruitmentState):
        """流程 1: 系统初始化 (自动化建表)"""
        print("\n" + "="*50)
        print("--- Node: Initialize (Auto-Scaling Bitable) ---")
        print("="*50)
        
        # 定义完整表结构 (1=文本, 2=数字)
        schema = {
            "岗位描述": [
                {"field_name": "岗位名称", "type": "text"},
                {"field_name": "岗位要求", "type": "text"},
                {"field_name": "招聘人数", "type": "number"},
                {"field_name": "创建时间", "type": "text"}
            ],
            "简历池": [
                {"field_name": "候选人ID", "type": "text"},
                {"field_name": "姓名", "type": "text"},
                {"field_name": "性别", "type": "text"},
                {"field_name": "年龄", "type": "number"},
                {"field_name": "学历", "type": "text"},
                {"field_name": "工作经验", "type": "text"},
                {"field_name": "技能标签", "type": "text"},
                {"field_name": "简历内容", "type": "text"},
                {"field_name": "筛选状态", "type": "text"},
                {"field_name": "相似度评分", "type": "number"},
                {"field_name": "面试状态", "type": "text"},
                {"field_name": "Offer状态", "type": "text"}
            ],
            "面试官可用时间": [
                {"field_name": "面试官ID", "type": "text"},
                {"field_name": "日期", "type": "text"},
                {"field_name": "时段", "type": "text"},
                {"field_name": "具体时间", "type": "text"},
                {"field_name": "可用状态", "type": "text"}
            ],
            "面试邀约记录": [
                {"field_name": "邀约ID", "type": "text"},
                {"field_name": "候选人ID", "type": "text"},
                {"field_name": "候选人姓名", "type": "text"},
                {"field_name": "可选时间段1", "type": "text"},
                {"field_name": "可选时间段2", "type": "text"},
                {"field_name": "可选时间段3", "type": "text"},
                {"field_name": "选择的时间段", "type": "text"},
                {"field_name": "邀约状态", "type": "text"},
                {"field_name": "邀约时间", "type": "text"},
                {"field_name": "回复时间", "type": "text"}
            ],
            "面试安排": [
                {"field_name": "面试ID", "type": "text"},
                {"field_name": "候选人ID", "type": "text"},
                {"field_name": "面试官ID", "type": "text"},
                {"field_name": "面试时间", "type": "text"},
                {"field_name": "面试状态", "type": "text"},
                {"field_name": "面试反馈", "type": "text"},
                {"field_name": "评估结果", "type": "number"},
                {"field_name": "安排状态", "type": "text"}
            ],
            "招聘数据分析": [
                {"field_name": "报告类型", "type": "text"},
                {"field_name": "报告内容", "type": "text"},
                {"field_name": "生成时间", "type": "text"}
            ]
        }

        table_ids = {}
        for table_name, fields in schema.items():
            tid = await self.feishu.get_table_id_by_name(table_name)
            if not tid:
                print(f"Table '{table_name}' not found. Creating...")
                tid = await self.feishu.create_table(table_name, fields)
            else:
                print(f"Found existing table '{table_name}': {tid}")
                # 清空表格历史数据
                await self.feishu.clear_table(tid)
            table_ids[table_name] = tid
        
        # 尝试从“岗位描述”表读取 JD
        records = await self.feishu.list_records(table_ids["岗位描述"])
        if records:
            jd = records[0].get("岗位要求", state["jd"])
            num_candidates = int(records[0].get("招聘人数", state["num_candidates_to_generate"]))
            print(f"Loaded JD from Bitable: {jd[:50]}...")
            
            # 删除多余的岗位描述记录，仅保留第一条
            if len(records) > 1:
                print(f"Found {len(records)} JD records, deleting {len(records)-1} extra records...")
                for rec in records[1:]:
                    if "record_id" in rec:
                        # 调用删除记录方法
                        await self.feishu.delete_record(table_ids["岗位描述"], rec["record_id"])
        else:
            jd = state["jd"]
            num_candidates = state["num_candidates_to_generate"]
            print("No JD found in Bitable, initializing from environment...")
            await self.feishu.add_record(table_ids["岗位描述"], {
                "岗位名称": "Python Developer",
                "岗位要求": jd,
                "招聘人数": num_candidates,
                "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        return {**state, "table_ids": table_ids, "jd": jd, "num_candidates_to_generate": num_candidates, "current_step": "initialize"}

    async def node_generate_candidates(self, state: RecruitmentState):
        """流程 2: 简历投递"""
        print("\n" + "="*50)
        print("--- Node: Generate Candidates ---")
        print("="*50)
        jd = state["jd"]
        num = state["num_candidates_to_generate"]
        
        print(f"Generating {num} candidates based on JD...")
        resumes = []
        for i in range(num):
            resume_data = await self.candidate.generate_resume(jd)
            record_id = await self.feishu.add_record(state["table_ids"]["简历池"], resume_data)
            resume_data["record_id"] = record_id
            resumes.append(resume_data)
            print(f"[{i+1}/{num}] Candidate '{resume_data['姓名']}' submitted resume. (ID: {record_id})")
            
        return {**state, "resumes": resumes, "current_step": "generate_candidates"}

    async def node_set_availability(self, state: RecruitmentState):
        """流程 3: 面试官设置时间"""
        print("\n" + "="*50)
        print("--- Node: Set Availability ---")
        print("="*50)
        slots_data = await self.interviewer.set_availability()
        
        print(f"Interviewer setting {len(slots_data)} available slots for 7 days later...")
        # 写入飞书
        record_ids = await self.feishu.batch_add_records(state["table_ids"]["面试官可用时间"], slots_data)
        for i, rid in enumerate(record_ids):
            slots_data[i]["record_id"] = rid
            print(f"Slot created: {slots_data[i]['日期']} {slots_data[i]['具体时间']} ({slots_data[i]['时段']})")
            
        return {**state, "slots": slots_data, "current_step": "set_availability"}

    async def node_screening(self, state: RecruitmentState):
        """流程 4: 简历筛选"""
        print("\n" + "="*50)
        print("--- Node: Screening ---")
        print("="*50)
        jd = state["jd"]
        resumes = state["resumes"]
        
        print(f"HR screening {len(resumes)} resumes...")
        updated_resumes = []
        for r in resumes:
            result = await self.hr.screen_resume(jd, r["简历内容"])
            r["相似度评分"] = result["score"]
            r["筛选状态"] = result["status"]
            print(f"Screened '{r['姓名']}': Score {r['相似度评分']}, Result: {r['筛选状态']}")
            # 更新飞书
            await self.feishu.update_record(
                state["table_ids"]["简历池"], 
                r["record_id"], 
                {"筛选状态": r["筛选状态"], "相似度评分": r["相似度评分"]}
            )
            updated_resumes.append(r)
            
        return {**state, "resumes": updated_resumes, "current_step": "screening"}

    async def node_scheduling(self, state: RecruitmentState):
        """流程 5: 面试安排 (HR) - 给候选人发送多个可选时间段"""
        print("\n" + "="*50)
        print("--- Node: Scheduling ---")
        print("="*50)
        # 挑选筛选通过且未安排的候选人
        candidates = [r for r in state["resumes"] if r["筛选状态"] == "通过"]
        # 获取可用时间槽
        available_slots = [s for s in state["slots"] if s["可用状态"] == "可用"]
        
        print(f"HR preparing interview invitations for {len(candidates)} passed candidates...")
        invitations = []
        
        for cand in candidates:
            # 为每个候选人选取最多3个可用时间段
            selected_slots = available_slots[:min(3, len(available_slots))]
            if not selected_slots:
                print(f"No available slots for candidate {cand['姓名']}, skipping...")
                continue
                
            # 创建邀约记录
            invitation_id = f"INV_{cand['候选人ID']}"
            invitation_fields = {
                "邀约ID": invitation_id,
                "候选人ID": cand["候选人ID"],
                "候选人姓名": cand["姓名"],
                "可选时间段1": f"{selected_slots[0]['日期']} {selected_slots[0]['具体时间']}",
                "可选时间段2": f"{selected_slots[1]['日期']} {selected_slots[1]['具体时间']}" if len(selected_slots) >=2 else "",
                "可选时间段3": f"{selected_slots[2]['日期']} {selected_slots[2]['具体时间']}" if len(selected_slots) >=3 else "",
                "邀约状态": "待回复",
                "邀约时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            record_id = await self.feishu.add_record(state["table_ids"]["面试邀约记录"], invitation_fields)
            invitation_fields["record_id"] = record_id
            invitation_fields["available_slots"] = selected_slots
            invitations.append(invitation_fields)
            
            print(f"Sent invitation to '{cand['姓名']}' with {len(selected_slots)} time slots.")
                
        return {**state, "invitations": invitations, "current_step": "scheduling"}

    async def node_confirm_interview(self, state: RecruitmentState):
        """流程 5 step 7-8: 候选人选择面试时间段"""
        print("\n" + "="*50)
        print("--- Node: Confirm Interview ---")
        print("="*50)
        invitations = state["invitations"]
        interviews = []
        updated_invitations = []
        
        for inv in invitations:
            # 候选人选择时间段
            selected_idx = await self.candidate.decide_interview(inv)
            inv["回复时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if selected_idx >= 0:
                # 候选人选择了时间段
                selected_slot = inv["available_slots"][selected_idx]
                selected_time = f"{selected_slot['日期']} {selected_slot['具体时间']}"
                inv["选择的时间段"] = selected_time
                inv["邀约状态"] = "已确认"
                
                # 更新邀约记录表
                await self.feishu.update_record(
                    state["table_ids"]["面试邀约记录"],
                    inv["record_id"],
                    {
                        "选择的时间段": selected_time,
                        "邀约状态": "已确认",
                        "回复时间": inv["回复时间"]
                    }
                )
                
                # 占用时间槽
                await self.feishu.update_record(
                    state["table_ids"]["面试官可用时间"],
                    selected_slot["record_id"],
                    {"可用状态": "已占用"}
                )
                
                # 创建面试安排记录
                interview_fields = {
                    "面试ID": f"INT_{inv['候选人ID']}",
                    "候选人ID": inv["候选人ID"],
                    "面试官ID": selected_slot["面试官ID"],
                    "面试时间": selected_time,
                    "面试状态": "待进行",
                    "安排状态": "已确认"
                }
                record_id = await self.feishu.add_record(state["table_ids"]["面试安排"], interview_fields)
                interview_fields["record_id"] = record_id
                interview_fields["slot_record_id"] = selected_slot["record_id"]
                interviews.append(interview_fields)
                print(f"Interview confirmed for '{inv['候选人姓名']}' at {selected_time}.")
            else:
                # 候选人对所有时间段都不满意
                inv["邀约状态"] = "已拒绝"
                await self.feishu.update_record(
                    state["table_ids"]["面试邀约记录"],
                    inv["record_id"],
                    {
                        "邀约状态": "已拒绝",
                        "回复时间": inv["回复时间"]
                    }
                )
                print(f"Candidate '{inv['候选人姓名']}' rejected all time slots.")
                
            updated_invitations.append(inv)
            
        return {**state, "interviews": interviews, "invitations": updated_invitations, "current_step": "confirm_interview"}

    async def node_interviewing(self, state: RecruitmentState):
        """流程 6: 面试执行"""
        print("\n" + "="*50)
        print("--- Node: Interviewing ---")
        print("="*50)
        jd = state["jd"]
        # 仅处理已确认的面试
        confirmed_interviews = [inv for inv in state["interviews"] if inv["安排状态"] == "已确认"]
        
        print(f"Interviewer conducting {len(confirmed_interviews)} interviews...")
        # 预先一次性生成面试题，避免重复调用大模型
        print("Generating interview question bank...")
        all_questions = await self.interviewer.generate_questions(jd, num_questions=10)
        
        updated_interviews = []
        for inv in confirmed_interviews:
            print(f"Conducting MCQ interview for candidate {inv['候选人ID']}...")
            # 1. 使用预先生成的题目
            questions = all_questions
            # 2. 答题
            answers = await self.candidate.answer_questions(questions)
            # 3. 评分
            result = self.interviewer.evaluate_performance(questions, answers)
            
            inv["面试反馈"] = result["feedback"]
            inv["评估结果"] = result["score"]
            inv["面试状态"] = "已完成"
            print(f"Interview finished. Result: {inv['面试反馈']}")
            
            # 更新面试表
            await self.feishu.update_record(
                state["table_ids"]["面试安排"], 
                inv["record_id"], 
                {"面试反馈": inv["面试反馈"], "评估结果": inv["评估结果"], "面试状态": inv["面试状态"]}
            )
            
            # 更新简历池中的面试状态
            for resume in state["resumes"]:
                if resume["候选人ID"] == inv["候选人ID"]:
                    resume["面试状态"] = "已完成"
                    await self.feishu.update_record(
                        state["table_ids"]["简历池"],
                        resume["record_id"],
                        {"面试状态": "已完成"}
                    )
                    break
                    
            updated_interviews.append(inv)
            
        return {**state, "interviews": updated_interviews, "current_step": "interviewing"}

    async def node_offer_decision(self, state: RecruitmentState):
        """流程 7: 结果处理 (HR 发 Offer & 候选人回复)"""
        print("\n" + "="*50)
        print("--- Node: Offer Decision ---")
        print("="*50)
        interviews = state["interviews"]
        resumes = state["resumes"]
        
        for inv in interviews:
            if inv["面试状态"] == "已完成":
                print(f"Processing final decision for candidate {inv['候选人ID']}...")
                # HR 决定是否发 Offer
                offer_status = await self.hr.make_final_decision(inv["面试反馈"])
                
                # 如果 HR 发了 Offer，候选人决定是否接受
                if offer_status == OfferStatus.SENT.value:
                    print(f"HR SENT Offer to candidate {inv['候选人ID']}. Waiting for candidate response...")
                    final_status = await self.candidate.decide_offer(inv)
                else:
                    print(f"HR REJECTED candidate {inv['候选人ID']}.")
                    final_status = OfferStatus.REJECTED.value # HR 拒信
                
                # 更新简历表
                for r in resumes:
                    if r["候选人ID"] == inv["候选人ID"]:
                        r["Offer状态"] = final_status
                        await self.feishu.update_record(
                            state["table_ids"]["简历池"], 
                            r["record_id"], 
                            {"Offer状态": r["Offer状态"]}
                        )
                        print(f"Final status for {r['姓名']}: {final_status}")
                        
        return {**state, "resumes": resumes, "current_step": "offer_decision"}

    async def node_reporting(self, state: RecruitmentState):
        """流程 8: 数据分析"""
        print("--- Node: Reporting ---")
        report = await self.hr.generate_report(state["resumes"])
        print("\n=== Final Recruitment Report ===\n")
        print(report)
        
        # 写入飞书
        from datetime import datetime
        await self.feishu.add_record(state["table_ids"]["招聘数据分析"], {
            "报告类型": "招聘全流程分析报告",
            "报告内容": report,
            "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return {**state, "current_step": "finished", "is_finished": True}

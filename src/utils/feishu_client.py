import subprocess
import json
import os
import asyncio
import random
import tempfile
from typing import List, Dict, Any, Optional

class FeishuClient:
    def __init__(self, app_id: Optional[str] = None, app_secret: Optional[str] = None, base_id: Optional[str] = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_id = base_id
        
        # 判定是否为 Mock 模式：凭证缺失或包含占位符
        self.is_mock = (
            not (app_id and app_secret and base_id) or 
            "xxx" in (app_id or "") or 
            "xxx" in (app_secret or "")
        )
        
        if self.is_mock:
            print("Warning: Running in MOCK mode due to missing or invalid credentials.")
        else:
            # 初始化本地 lark-cli 配置，确保环境独立性
            try:
                self._setup_local_config(app_id, app_secret)
                print(f"Lark CLI localized config initialized for App ID: {app_id}")
            except Exception as e:
                print(f"Warning: Failed to setup local Lark CLI config: {e}")

    def _setup_local_config(self, app_id: str, app_secret: str):
        """创建项目本地的 .lark-cli 配置，避免依赖系统全局配置"""
        config_dir = os.path.join(os.getcwd(), ".lark-cli")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        config_path = os.path.join(config_dir, "config.json")
        config_data = {
            "apps": [
                {
                    "appId": app_id,
                    "appSecret": app_secret,
                    "brand": "feishu",
                    "name": "default"
                }
            ],
            "current": "default"
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
            
        # 设置环境变量，让 lark-cli 查找当前目录下的配置
        # 在 Windows 上 lark-cli 查找 USERPROFILE/.lark-cli/config.json
        # 我们在 _run_cli 中动态注入该环境变量
        self.local_home = os.getcwd()

    def _run_cli(self, args: List[str]) -> Dict[str, Any]:
        """运行 lark-cli 命令并返回 JSON 结果"""
        cmd = ["lark-cli"] + args
        try:
            env = os.environ.copy()
            # 注入本地配置路径（重定向 USERPROFILE/HOME）
            if hasattr(self, 'local_home'):
                env["USERPROFILE"] = self.local_home
                env["HOME"] = self.local_home
            
            if self.app_id: env["LARK_APP_ID"] = self.app_id
            if self.app_secret: env["LARK_APP_SECRET"] = self.app_secret
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env, shell=True, encoding='utf-8')
            stdout = result.stdout.strip()
            
            if not stdout:
                return {}
                
            # lark-cli 可能会在 JSON 前后输出一些非 JSON 内容（如警告或日志）
            # 尝试提取 JSON 部分
            try:
                # 寻找第一个 { 和最后一个 }
                start = stdout.find('{')
                end = stdout.rfind('}') + 1
                if start != -1 and end != 0:
                    return json.loads(stdout[start:end])
                return json.loads(stdout)
            except json.JSONDecodeError:
                return {"raw_output": stdout}
                
        except subprocess.CalledProcessError as e:
            # 错误处理：如果包含权限错误或 token 失效，抛出更清晰的异常
            err_msg = (e.stderr or "").strip() or (e.stdout or "").strip()
            if not err_msg:
                err_msg = f"Exit code {e.returncode} with no output."
                
            if "permission" in err_msg.lower():
                raise Exception(f"Feishu Permission Denied: 请检查应用是否已添加到多维表格中。详情: {err_msg}")
            raise Exception(f"Lark CLI execution failed: {err_msg}\nCommand: {' '.join(cmd)}")

    async def list_records(self, table_id: str, filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出表格中的所有记录"""
        if self.is_mock: return []
        
        args = ["base", "+record-list", "--base-token", self.base_id, "--table-id", table_id, "--as", "bot"]
        res = self._run_cli(args)
        
        # 兼容嵌套在 data 中的情况
        data = res.get("data", res) if isinstance(res, dict) else res
        items = data.get("items", []) if isinstance(data, dict) else []
        
        # 返回 fields 内容，并带上 record_id
        result = []
        for item in items:
            fields = item.get("fields", {})
            record_id = item.get("record_id") or item.get("id")
            if record_id:
                fields["record_id"] = record_id
            result.append(fields)
        return result

    async def add_record(self, table_id: str, fields: Dict[str, Any]) -> str:
        """向表格添加一条记录"""
        if self.is_mock: 
            return f"mock_rec_{random.randint(1000, 9999)}"
            
        # 使用临时文件传递 JSON，避免 Windows 命令行长度限制和转义问题
        temp_dir = os.path.join(os.getcwd(), ".tmp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8', dir=temp_dir) as tf:
            json.dump(fields, tf, ensure_ascii=False)
            temp_path = tf.name
            
        # 获取相对路径 (lark-cli 要求相对路径)
        rel_path = os.path.relpath(temp_path, os.getcwd())
            
        try:
            args = ["base", "+record-upsert", "--base-token", self.base_id, "--table-id", table_id, "--json", f"@{rel_path}", "--as", "bot"]
            res = self._run_cli(args)
            
            # 兼容各种嵌套结构
            data = res.get("data", res) if isinstance(res, dict) else res
            if not isinstance(data, dict):
                return "unknown_id"
                
            # 1. 尝试从 record 对象中获取 (upsert 常用)
            record_obj = data.get("record")
            if isinstance(record_obj, dict):
                # 兼容 record_id_list (lark-cli base +record-upsert 结构)
                id_list = record_obj.get("record_id_list")
                if id_list and isinstance(id_list, list) and len(id_list) > 0:
                    return id_list[0]
                    
                record_id = record_obj.get("record_id") or record_obj.get("id")
                if record_id: return record_id
                
            # 2. 尝试从根部获取
            record_id = data.get("record_id") or data.get("id")
            if not record_id:
                print(f"Warning: Could not find record_id in response: {res}")
                return "unknown_id"
            return record_id
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def batch_add_records(self, table_id: str, records: List[Dict[str, Any]]) -> List[str]:
        """批量添加记录"""
        if self.is_mock:
            return [f"mock_rec_{random.randint(1000, 9999)}" for _ in records]
        
        ids = []
        for r in records:
            ids.append(await self.add_record(table_id, r))
        return ids

    async def update_record(self, table_id: str, record_id: str, fields: Dict[str, Any]):
        """更新表格中的一条记录"""
        if self.is_mock:
            print(f"Mock: Updating record {record_id} in {table_id} with fields {fields}")
            return
            
        # 使用临时文件传递 JSON，避免 Windows 命令行长度限制和转义问题
        temp_dir = os.path.join(os.getcwd(), ".tmp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8', dir=temp_dir) as tf:
            json.dump(fields, tf, ensure_ascii=False)
            temp_path = tf.name
            
        # 获取相对路径 (lark-cli 要求相对路径)
        rel_path = os.path.relpath(temp_path, os.getcwd())
            
        try:
            args = ["base", "+record-upsert", "--base-token", self.base_id, "--table-id", table_id, "--record-id", record_id, "--json", f"@{rel_path}", "--as", "bot"]
            self._run_cli(args)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def delete_record(self, table_id: str, record_id: str):
        """删除表格中的一条记录"""
        if self.is_mock:
            print(f"Mock: Deleting record {record_id} from {table_id}")
            return
            
        args = ["base", "+record-delete", "--base-token", self.base_id, "--table-id", table_id, "--record-id", record_id, "--as", "bot", "--yes"]
        self._run_cli(args)

    async def clear_table(self, table_id: str):
        """清空表格中的所有记录"""
        if self.is_mock:
            print(f"Mock: Clearing all records from {table_id}")
            return
            
        # 直接获取所有记录ID，不需要解析内容
        args = ["base", "+record-list", "--base-token", self.base_id, "--table-id", table_id, "--as", "bot"]
        res = self._run_cli(args)
        
        # 提取所有record_id
        record_ids = []
        if isinstance(res, dict):
            data = res.get("data", res)
            if isinstance(data, dict):
                # 从 record_id_list 中获取所有记录ID
                record_ids = data.get("record_id_list", [])
                if not record_ids:
                    # 兼容其他可能的返回格式
                    items = data.get("items", [])
                    for item in items:
                        if isinstance(item, dict):
                            rid = item.get("record_id") or item.get("id")
                            if rid:
                                record_ids.append(rid)
        
        if not record_ids:
            print(f"No records found in table {table_id}")
            return
            
        print(f"Clearing {len(record_ids)} records from table {table_id}...")
        for rid in record_ids:
            print(f"Deleting record: {rid}")
            await self.delete_record(table_id, rid)

    async def delete_table(self, table_id: str):
        """删除整个表格"""
        if self.is_mock:
            print(f"Mock: Deleting table {table_id}")
            return
            
        args = ["base", "+table-delete", "--base-token", self.base_id, "--table-id", table_id, "--as", "bot", "--yes"]
        self._run_cli(args)
        print(f"Table {table_id} deleted successfully.")

    async def batch_update_records(self, table_id: str, records: List[Dict[str, Any]]):
        """批量更新记录"""
        if self.is_mock: return
        tasks = [self.update_record(table_id, r['record_id'], r['fields']) for r in records]
        await asyncio.gather(*tasks)

    async def get_table_id_by_name(self, table_name: str) -> Optional[str]:
        """根据表名获取 table_id，不存在则返回 None"""
        if self.is_mock:
            return f"mock_table_id_{table_name}"
            
        args = ["base", "+table-list", "--base-token", self.base_id, "--as", "bot"]
        res = self._run_cli(args)
        
        # 兼容两种结构：直接返回 items/tables 或嵌套在 data 中
        data = res.get("data", res) if isinstance(res, dict) else res
        
        # 尝试不同的列表键
        items = []
        if isinstance(data, dict):
            items = data.get("items") or data.get("tables") or []
        
        for table in items:
            if table.get("name") == table_name:
                # 尝试不同的 ID 键
                return table.get("table_id") or table.get("tableId") or table.get("id")
        return None

    async def create_table(self, table_name: str, fields: List[Dict[str, Any]]) -> str:
        """自动化创建表格及字段"""
        if self.is_mock:
            print(f"Mock: Creating table '{table_name}' with fields {fields}")
            return f"mock_tbl_{table_name}"
            
        # 防止频率限制
        await asyncio.sleep(1)
        
        # fields 格式: [{"field_name": "xxx", "type": 1}, ...]
        fields_json = json.dumps(fields)
        args = ["base", "+table-create", "--base-token", self.base_id, "--name", table_name, "--fields", fields_json, "--as", "bot"]
        res = self._run_cli(args)
        
        # 兼容嵌套在 data 中的情况
        data = res.get("data", res) if isinstance(res, dict) else res
        table_id = None
        if isinstance(data, dict):
            # 优先从 table 对象中获取（+table-create 结构）
            table_obj = data.get("table")
            if isinstance(table_obj, dict):
                table_id = table_obj.get("id") or table_obj.get("table_id")
            
            # 兜底从根部获取
            if not table_id:
                table_id = data.get("table_id") or data.get("id") or data.get("tableId")
        
        if not table_id:
            raise Exception(f"Failed to create table '{table_name}': {res}")
            
        print(f"Successfully created table '{table_name}' (ID: {table_id})")
        return table_id

'''
Author: suntututut wuyaosantu@qq.com
Date: 2025-12-11 13:53:40
LastEditors: suntututut wuyaosantu@qq.com
LastEditTime: 2025-12-11 20:29:41
FilePath: /AutoEmail/backend/app/database.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Session, create_engine, select
from pathlib import Path



BASE_DIR = Path(__file__).parent.parent / "storage" / "database"
BASE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "resume.db"
SQLITE_URL = f"sqlite:///{DB_PATH}"



class Resume(SQLModel, table=True):
    
    id: Optional[int] = Field(default=None, primary_key=True)
    uid: str = Field(unique=True, index=True)

    # 基本信息
    name: str
    phone_num: str
    send_time: Optional[str] = None   # 发送时间

    job_position: Optional[str] = Field(default=None, index=True) # 职位名称
    # 文件路径 (重点：我们只存路径字符串，不存文件本身)
    # raw_email_path: Optional[str] = None  # .eml 文件在哪

    attachment_path: Optional[str] = None # .pdf/.docx 简历在哪
    collection_path: Optional[str] = None
    # 状态标记 (用来管理流程)
    # new: 刚存入 -> processed: 已处理
    status: str = Field(default="new")

    # 记录入库时间
    created_at: datetime = Field(default_factory=datetime.now)



class ResumeInit:
    def __init__(self) -> None:
        self.engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

        self.init_db()

    def init_db(self):
        """初始化数据库：如果没有表，就创建表"""

        SQLModel.metadata.create_all(self.engine)
        print("✅ 数据库表结构已初始化！")

    def create_resume(self, resume_data: dict):
        """
        存入一份新简历 (会自动查重)
        :param resume_data: 一个字典，包含 name, phone, job 等纯文本信息的字典
        """
        # 建立一次会话 (Session)
        with Session(self.engine) as session:
            # --- A. 查重逻辑 ---
            # 翻译成 SQL: SELECT * FROM resume WHERE uid = '...'
            statement = select(Resume).where(Resume.uid == resume_data['uid'])
            existing_resume = session.exec(statement).first()
            
            if existing_resume:
                print(f"⚠️ 简历已存在 (UID: {resume_data['uid']})，跳过保存。")
                return None

            # --- B. 插入逻辑 ---
            # 把字典转换成 Resume 对象 (例如: {"uid": "1", ...} -> Resume(uid="1", ...))
            new_resume = Resume(**resume_data)
            
            session.add(new_resume)  # 放入暂存区
            session.commit()         # 提交到数据库 (相当于按保存键)
            session.refresh(new_resume) # 刷新一下，拿回自动生成的 id
            
            print(f"💾 [入库成功] ID: {new_resume.id} | {new_resume.name}")
            return new_resume

    def get_all_resumes(self):
        """查询所有简历"""
        with Session(self.engine) as session:
            statement = select(Resume).order_by(Resume.id.desc())
            results = session.exec(statement).all()
            return results




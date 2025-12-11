'''
Author: suntututut wuyaosantu@qq.com
Date: 2025-12-11 18:22:07
LastEditors: suntututut wuyaosantu@qq.com
LastEditTime: 2025-12-11 21:10:44
FilePath: /AutoEmail/frontend/app/demo.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from pathlib import Path
import os
import sys
import pandas as pd


# --- 1. 环境配置 (连接后端数据库) ---
# 将项目根目录加入 sys.path，保证能找到 backend 包
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent  # /home/wy/AutoEmail
sys.path.append(str(project_root))

# 导入入库逻辑
from backend.app.database import ResumeInit, Session, select, Resume


storage_base_path = Path(__file__).parent.parent.parent / "backend" / "storage"
attachments_path = storage_base_path / "attachments"
collection_path = storage_base_path / "collection"
database_path = storage_base_path / "database"




class ResumeDataManager:
    '''
        查数据库
        存数据库
        存硬盘
    '''
    def __init__(self) -> None:
        self.Resume_init = ResumeInit()
        self.engine = self.Resume_init.engine

    def is_user_exits(self, name, phone) -> bool:
        ''' 查重 '''

        with Session(self.engine) as session:
            statement = select(Resume).where((Resume.name == name) & (Resume.phone_num == phone))
            res = session.exec(statement).first()

            return res is not None


    def save(self, resume: dict, resume_file, portfolio_file):

        data = resume
        name = data.get("name")


        res_ext = resume_file.name.split('.')[-1]
        res_filename = f"{name}_resume.{res_ext}"
        res_path = os.path.join(attachments_path, res_filename)
        with open(res_path, "wb") as f:
            f.write(resume_file.getbuffer())
        data["attachment_path"] = res_path


        if portfolio_file:
            port_ext = portfolio_file.name.split('.')[-1]
            port_filename = f"{name}_portfolio.{port_ext}"
            port_path = os.path.join(collection_path, port_filename)
            with open(port_path, "wb") as f:
                f.write(portfolio_file.getbuffer())


            data["collection_path"] = port_path
        else: data["collection_path"] = None

        self.Resume_init.create_resume(data)

        return True

    def fetch_all_resumes_as_df(self):
        """
        获取所有简历数据，并直接转换为 Pandas DataFrame，方便前端排序和筛选
        """
        with Session(self.engine) as session:
            statement = select(Resume)
            results = session.exec(statement).all()
            
            # 将 SQLModel 对象列表转换为字典列表
            data = [resume.model_dump() for resume in results]
            
            if not data:
                return pd.DataFrame() # 返回空表防止报错

            df = pd.DataFrame(data)
            
            # 确保时间列是 datetime 类型，方便排序
            df["send_time"] = pd.to_datetime(df["send_time"])
            return df


    def update_resume_status(self, resume_id: int, new_status: str) -> bool:
        """
        根据 ID 更新简历状态
        """
        with Session(self.engine) as session:
            # 1. 根据 ID 查找记录
            statement = select(Resume).where(Resume.id == resume_id)
            resume = session.exec(statement).first()
            
            if resume:
                # 2. 修改状态
                resume.status = new_status
                # 3. 提交更改
                session.add(resume)
                session.commit()
                session.refresh(resume)
                return True
            else:
                return False


                

if __name__ == "__main__":
    rdm = ResumeDataManager()
    
    print(rdm.is_user_exits(name='无要', phone='124241241'))


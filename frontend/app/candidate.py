import streamlit as st
import os
import sys
from datetime import datetime
from sqlmodel import Session, select
from pathlib import Path
from senddb import ResumeDataManager
import hashlib


# 定义大小限制 (字节)
LIMIT_10MB = 10 * 1024 * 1024
LIMIT_200MB = 200 * 1024 * 1024


class CandidatePage:
    """
    页面展示类：负责 UI 渲染、状态管理和输入校验
    """
    def __init__(self, data_manager: ResumeDataManager):
        self.manager = data_manager
        
        # 1. 初始化页面配置
        st.set_page_config(
            page_title="职位申请通道", 
            page_icon="🧑‍💼", 
            layout="centered"
        )
        
        # 2. 初始化 Session State
        self._init_session_state()

    def _init_session_state(self):
        """初始化防抖和计数状态"""
        if "has_submitted" not in st.session_state:
            st.session_state.has_submitted = False
        if "submit_ts" not in st.session_state:
            st.session_state.submit_ts = None
        if "submit_count" not in st.session_state:
            st.session_state.submit_count = 0

    def check_frequency_limit(self, threshold_sec: int = 10, max_per_session: int = 3) -> str | None:
        """检查提交频率"""
        now = datetime.now()
        
        # 检查时间间隔
        if st.session_state.submit_ts:
            delta = (now - st.session_state.submit_ts).total_seconds()
            if delta < threshold_sec:
                return f"提交过快，请 {int(threshold_sec - delta)} 秒后再试。"
        
        # 检查总次数
        if st.session_state.submit_count >= max_per_session:
            return "本次会话提交次数过多，请稍后再试或刷新页面。"
            
        return None

    def render(self):
        """渲染主界面"""
        st.title("加入我们")
        st.markdown("请填写基本信息并上传您的附件。")

        with st.form("apply_form", clear_on_submit=False):
            # --- 表单区域 ---
            st.subheader("1. 基本信息")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("您的姓名 *")
            with col2:
                contact = st.text_input("联系方式 (手机) *")

            job_options = [
                "产品经理", "产品运营", "商业化运营", "BD", "数据分析",
                "算法工程师", "前端工程师", "后端工程师", "全栈工程师",
                "移动端工程师", "测试工程师", "设计师", "市场与品牌", "人力与行政"
            ]
            position = st.selectbox("申请岗位 *", options=["请选择"] + job_options)
            
            st.subheader("2. 附件上传")
            st.markdown("**📄 个人简历 (必填)**")
            resume_file = st.file_uploader("支持 PDF, Word (最大 10MB)", type=['pdf', 'docx', 'doc'])
            
            st.markdown("**🎬 作品集/视频 (选填)**")
            portfolio_file = st.file_uploader("支持视频 MP4, MOV (最大 200MB)", type=['mp4', 'mov', 'pdf'])
            st.caption("提示：上传大文件时请耐心等待，直到文件名下方显示文件大小为止。")

            # --- 提交逻辑 ---
            submitted = st.form_submit_button(
                "确认提交申请",
                use_container_width=True,
                disabled=st.session_state.has_submitted
            )

            if submitted:
                self._handle_submission(name, contact, position, resume_file, portfolio_file)


    def generate_hash_uid(self, name: str, phone: str) -> str:
        """
        输入：张三, 13800138000
        输出：md5(张三+13800138000) -> 比如 "a1b2c3d4..."
        """
        # 1. 拼接字符串 (加一个盐/分隔符防止混淆，比如 name='1' phone='23' 和 name='12' phone='3')
        raw_str = f"{name}_{phone}"
        
        # 2. 【关键】中文必须编码为 bytes，通常使用 utf-8
        data_bytes = raw_str.encode("utf-8")
        
        # 3. 计算 MD5 (或者 SHA256)
        md5_hash = hashlib.md5(data_bytes).hexdigest()
        
        return md5_hash



    def _handle_submission(self, name, contact, position, resume_file, portfolio_file):
        """处理提交点击事件"""
        
        # 1. 基础非空校验
        if not name or not contact:
            st.error("❌ 请填写姓名和联系方式！")
            return
        if not resume_file:
            st.error("❌ 请上传您的简历！")
            return
        if position == "请选择":
            st.error("❌ 请选择申请岗位！")
            return
        if len(contact) != 11:
            st.error("❌ 请输入正确的号码")
            return

        # 2. 频率校验
        freq_msg = self.check_frequency_limit()
        if freq_msg:
            st.error(f"❌ {freq_msg}")
            return

        # 3. 文件大小校验
        if resume_file.size > LIMIT_10MB:
            st.error(f"❌ 简历文件过大 ({resume_file.size/1024/1024:.2f} MB)！请压缩到 10MB 以内。")
            return
        if portfolio_file and portfolio_file.size > LIMIT_200MB:
            st.error(f"❌ 作品集文件过大 ({portfolio_file.size/1024/1024:.2f} MB)！请压缩到 200MB 以内。")
            return

        # 4. 业务逻辑校验 (查重)
        # 调用 Manager 层
        if self.manager.is_user_exits(name, contact):
            st.error("❌ 已提交过申请，请勿重复提交。")
            return


        uid = self.generate_hash_uid(name=name, phone = contact)
        with st.spinner("Up loading..."):
            resume = {
                    "uid":uid,
                    "name": name,
                    "phone_num": contact,
                    "job_position": position,
                    "send_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

                }
            

            # print(resume)
            success = self.manager.save(resume, resume_file, portfolio_file)
        # success = True
        # 6. 处理成功状态
        if success:
            st.success("✅ 提交成功！我们已收到您的申请，HR 将尽快与您联系。")
            st.balloons() # 撒花特效
            
            # 更新 Session 状态
            # has_submitted = True 会导致界面上的提交按钮变灰(disabled)
            st.session_state.has_submitted = True
            st.session_state.submit_ts = datetime.now()
            st.session_state.submit_count += 1 





if __name__ == "__main__":
    # 使用 session_state 缓存 ResumeDataManager 实例
    if "data_manager" not in st.session_state:
        st.session_state.data_manager = ResumeDataManager()
    
    if "ui" not in st.session_state:
        st.session_state.ui = CandidatePage(st.session_state.data_manager)
    
    st.session_state.ui.render()
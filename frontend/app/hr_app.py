import streamlit as st
import pandas as pd
import os
import sys
import base64
import mammoth
import mimetypes
from senddb import ResumeDataManager

# --- 预览工具类 ---
class FilePreviewer:
    @staticmethod
    def show_pdf(file_path):
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        st.markdown(f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf">', unsafe_allow_html=True)

    @staticmethod
    def show_docx(file_path):
        try:
            with open(file_path, "rb") as docx_file:
                result = mammoth.convert_to_html(docx_file)
                st.markdown(f'<div style="background:white;color:black;padding:20px;">{result.value}</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Word 解析失败: {e}")

    @staticmethod
    def render(file_path):
        if not file_path or not os.path.exists(file_path):
            st.warning("⚠️ 文件不存在")
            return
            
        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        
        with open(file_path, "rb") as f:
            st.download_button(f"📥 下载 ({file_name})", f, file_name=file_name)
        
        st.divider()
        if ext == ".pdf":
            FilePreviewer.show_pdf(file_path)
        elif ext == ".docx":
            FilePreviewer.show_docx(file_path)
        elif ext in [".mp4", ".mov", ".webm"]:
            st.video(file_path)
        elif ext in [".jpg", ".png"]:
            st.image(file_path)
        else:
            st.info("暂不支持预览此格式，请下载查看。")

\

# --- HR 面板类 ---
class HRDashboard:
    def __init__(self, manager):
        self.manager = manager
        st.set_page_config(page_title="HR 工作台", page_icon="💼", layout="wide")

    def update_status(self, resume_id, new_status):
        """
        调用 Manager 更新状态并刷新页面
        """
        # 调用 Manager 中新写的 update_resume_status 方法
        success = self.manager.update_resume_status(resume_id, new_status)
        
        if success:
            st.success(f"✅ 状态已更新为: {new_status}")
            st.rerun() # 立即刷新页面显示最新状态
        else:
            st.error("❌ 更新失败，未找到该候选人记录")

    def render(self):
        st.title("💼 候选人管理看板")
        df = self.manager.fetch_all_resumes_as_df()
        
        if df.empty:
            st.info("暂无简历")
            return

        with st.sidebar:
            st.header("🔍 筛选")
            jobs = list(df["job_position"].unique())
            sel_jobs = st.multiselect("岗位", jobs, default=jobs)
            kw = st.text_input("搜索姓名/电话")
            sort_opt = st.radio("排序", ["最新在前", "最早在前"])

        # 过滤
        if sel_jobs: df = df[df["job_position"].isin(sel_jobs)]
        if kw: df = df[df["name"].str.contains(kw) | df["phone_num"].str.contains(kw)]
        
        # 排序
        df = df.sort_values(by="send_time", ascending=(sort_opt == "最早在前"))

        # 表格显示
        st.subheader(f"📋 列表 ({len(df)}人)")
        
        # 定义显示的列 (注意：虽然这里不显示 ID，但 df 里必须有 id 列)
        display_cols = ["name", "phone_num", "job_position", "send_time", "status", "attachment_path", "collection_path"]
        
        column_config = {
            "name": "姓名", 
            "phone_num": "电话", 
            "job_position": "岗位",
            "send_time": st.column_config.DatetimeColumn("时间", format="MM-DD HH:mm"),
            "status": st.column_config.TextColumn("状态", width="small"),
            "attachment_path": st.column_config.TextColumn("简历", width="small"),
            "collection_path": st.column_config.TextColumn("作品集", width="small")
        }

        # 修复警告：use_container_width -> width="stretch"
        event = st.dataframe(
            df[display_cols],
            width="stretch",
            column_config=column_config,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        if event.selection.rows:
            idx = event.selection.rows[0]
            # 获取完整的一行数据 (包含 id)
            row = df.iloc[idx]
            self._render_detail(row)

    def _render_detail(self, row):
        st.markdown("---")
        st.subheader(f"👤 {row['name']} 详情")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("岗位", row['job_position'])
        c2.metric("电话", row['phone_num'])
        c3.metric("时间", row['send_time'].strftime("%Y-%m-%d %H:%M"))
        
        # --- 核心修改：状态修改区域 ---
        with c4:
            # 定义招聘流程的所有状态
            status_options = ["new", "pending", "interview", "offer", "rejected", "finished"]
            current_status = row['status']
            
            # 防止旧数据的状态不在选项列表中
            if current_status not in status_options:
                status_options.insert(0, current_status)
            
            # 使用 Selectbox 选择新状态
            # key 必须包含 id，确保切换不同人时组件重置
            new_status = st.selectbox(
                "当前状态 (点击修改)", 
                options=status_options,
                index=status_options.index(current_status),
                key=f"status_sel_{row['id']}" 
            )
            
            # 如果选中的状态和当前不一致，触发更新
            if new_status != current_status:
                # 传入 ID 和 新状态
                # 注意：row['id'] 需要确保 int 类型
                self.update_status(int(row['id']), new_status)

        col1, col2 = st.columns(2)
        with col1:
            st.info("📄 简历")
            # 使用 FilePreviewer (假设类已定义)
            FilePreviewer.render(row.get("attachment_path"))
        with col2:
            st.success("🎬 作品集")
            if row.get("collection_path"):
                FilePreviewer.render(row.get("collection_path"))
            else:
                st.caption("无作品集")

if __name__ == "__main__":
    manager = ResumeDataManager()
    app = HRDashboard(manager)
    app.render()
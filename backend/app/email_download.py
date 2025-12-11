'''
Author: suntututut wuyaosantu@qq.com
Date: 2025-12-10 15:32:02
LastEditors: suntututut wuyaosantu@qq.com
LastEditTime: 2025-12-11 16:48:33
FilePath: /AutoEmail/backend/app/download.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''


import os
import re
from sqlmodel import select
from imbox import Imbox
from pathlib import Path
from utils import load_config
from database import init_db, engine, Resume, create_resume, get_all_resumes, Session
import imaplib
from imaplib import IMAP4
import requests
from urllib.parse import unquote, urlparse

# 定义保存路径
BASE_DIR = Path(__file__).parent.parent / "storage"
EMAIL_DIR = BASE_DIR / "emails"       # 存原始 .eml
ATTACH_DIR = BASE_DIR / "attachments" # 存简历附件
EMAIL_DIR.mkdir(parents=True, exist_ok=True)
ATTACH_DIR.mkdir(parents=True, exist_ok=True)

class EmailDownloader:
    def __init__(self, config_path: Path):

        self.config = load_config(config_path)


        self._is_connected = False

        # 允许下载的扩展名白名单
        self.allowed_extensions = {'.pdf', '.docx', '.doc', '.jpg', '.png'}


    def _connect(self):

        if self._is_connected:
            return

        
        imaplib.Commands['ID'] = ('AUTH', 'AUTHENTICATED', 'SELECTED', 'LOGOUT')

        self.mailbox = Imbox(self.config['imap_server'], 
                        username=self.config['username'], 
                        password=self.config['imap_password'], 
                        ssl=True)

         # 发送 ID
        typ, data = self.mailbox.connection._simple_command(
            'ID', '("name" "Mozilla Thunderbird" "version" "102.0")'
        )
        # print("ID:", typ, data)

        # 只读选择 INBOX
        typ, data = self.mailbox.connection.select('INBOX', readonly=True)
        # print("SELECT:", typ, data)
        if typ != 'OK':
            raise IMAP4.error(f"Failed to select INBOX: {typ} {data}")


        print("✅ Connected to the email server")
        
        self._init_db()
        self._is_connected = True

    def _init_db(self):
        init_db()


    def _disconnect(self):
        if self._is_connected:
            self.mailbox.logout()
            print("Disconnected from the email server")
            self._is_connected = False
 
    
    def download_email(self):
        all_inbox_messages = self.mailbox.messages()

        return all_inbox_messages
        
    
    def sync_emalls_to_db(self):

        self._connect()

        
        with Session(engine) as session:
            statement = select(Resume.uid)
            results = session.exec(statement).all()
            existing_uids = set(str(uid) for uid in results) 
        
        print(f"✅ 本地已有 {len(existing_uids)} 封邮件。")
        
        
        
        
        all_inbox_messages = self.mailbox.messages()

        new_count = 0
        for uid, msg in all_inbox_messages:
            # if str(uid) in existing_uids:
            #     print(f"⚠️ 邮件已存在 (UID: {uid})，跳过保存。")
            #     continue
            

            # 1. 下载原始文件与附件

            eml_path = EMAIL_DIR / f"{msg.subject}.eml" 
            raw_bytes = msg.raw_email
            if isinstance(raw_bytes, str):
                raw_bytes = raw_bytes.encode("utf-8", errors="ignore")
                
            eml_path.write_bytes(raw_bytes)


            # 2) 保存附件（白名单过滤）
            att_files = []
            if msg.attachments:
                print(f"  📎 发现 {len(msg.attachments)} 个普通附件")
                for att in msg.attachments:
                    
                    filename = att.get("filename") or f"{uid}_attachment.bin"
                    # 简单清洗文件名
                    filename = filename.replace("/", "_").replace("\\", "_")
                    print(filename)
                    ext = Path(filename).suffix.lower()
                    if ext and ext not in self.allowed_extensions:
                        # print(f"跳过附件 {filename}，后缀 {ext} 不在白名单。")
                        continue

                    content = att.get("content")

                    if content:
                        path = ATTACH_DIR / filename
                        path.write_bytes(content.getvalue())
                        att_files.append(str(path))
            else:
                html_list = msg.body.get('html')
                
                self.download_cloud_file_safe(html_list, ATTACH_DIR)

                
                


           # 2. 构造数据
            resume_data = {
                "uid": str(uid),
                "subject": msg.subject,
                "sender": msg.sent_from[0]['email'],
                "send_time": str(msg.date),
                "email_body": msg.body['plain'][0] if msg.body['plain'] else "",
                "raw_email_path": str(eml_path),
                "attachment_path": ";".join(att_files) if att_files else None,
                "status": "new",
                # 如果你加了岗位提取功能
                # "job_position": extract_position_from_subject(msg.subject)
            }

            create_resume(resume_data)
            new_count += 1
        
        print(f"✅ 新邮件处理完成，共 {new_count} 封。")





    def download_cloud_file_safe(self, html_content_list, save_dir, cookie_str=None):
            """下载 QQ/网易大附件（含跳转页解析）。返回保存路径或 None。"""
            if not html_content_list or not isinstance(html_content_list, list):
                return None
            html_text = html_content_list[0] or ""

            # 邮件正文里的初始链接
            jump_links = re.findall(r'href=["\'](http[^"\']*(?:download|ftn|qqmail)[^"\']*)["\']',
                                    html_text, re.IGNORECASE)
            if not jump_links:
                return None

            session = requests.Session()
            session.headers.update({"User-Agent": "Mozilla/5.0"})
            if cookie_str:
                session.headers.update({"Cookie": cookie_str})

            allow_ext = {'.pdf', '.doc', '.docx', '.zip', '.rar', '.7z'}
            allow_ct_prefix = (
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument',
                'application/octet-stream',
            )

            def pick_filename(url, resp):
                cd = resp.headers.get("Content-Disposition", "")
                m = re.search(r'filename="?([^"]+)"?', cd)
                if m:
                    fname = m.group(1)
                else:
                    fname = os.path.basename(urlparse(url).path) or "downloaded_file.bin"
                fname = unquote(fname)
                fname = fname.replace("/", "_").replace("\\", "_")
                return fname

            def is_html(resp):
                return "text/html" in resp.headers.get("Content-Type", "").lower()

            def extract_direct_links(page_html):
                links = re.findall(r'https?://[^"\']*(?:download|ftn|qqmail)[^"\']*', page_html, re.IGNORECASE)
                # 兼容 downUrl = "..."
                links += re.findall(r'downUrl\s*[:=]\s*["\']([^"\']+)["\']', page_html, re.IGNORECASE)
                return links

            for jurl in jump_links:
                url = jurl.replace("&amp;", "&")
                print(f"☁️ 跳转页: {url[:80]}...")
                try:
                    resp = session.get(url, timeout=20, allow_redirects=True)
                except Exception as exc:
                    print(f"⚠️ 跳转失败: {exc}")
                    continue

                # 如果已经是文件响应，直接尝试保存
                if not is_html(resp):
                    fname = pick_filename(url, resp)
                    ext = Path(fname).suffix.lower()
                    ct = resp.headers.get("Content-Type", "").lower()
                    if ext in allow_ext or ct.startswith(allow_ct_prefix):
                        save_path = os.path.join(save_dir, fname)
                        with open(save_path, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        print(f"✅ 云附件下载成功: {save_path}")
                        return save_path
                    else:
                        print(f"⚠️ 非允许类型 ext={ext} ct={ct}，跳过")
                        continue

                # 跳转页是 HTML，再提取直链
                html = resp.text
                direct_links = extract_direct_links(html)
                if not direct_links:
                    print("⚠️ 跳转页未找到直链，可能需要登录/验证码")
                    continue

                for durl in direct_links:
                    durl = durl.replace("&amp;", "&")
                    print(f"➡️ 直链尝试: {durl[:80]}...")
                    try:
                        dresp = session.get(durl, timeout=20, allow_redirects=True, stream=True)
                    except Exception as exc:
                        print(f"⚠️ 直链请求失败: {exc}")
                        continue
                    if is_html(dresp):
                        print("⚠️ 直链仍返回 HTML，可能需登录/验证码，跳过")
                        continue
                    fname = pick_filename(durl, dresp)
                    ext = Path(fname).suffix.lower()
                    ct = dresp.headers.get("Content-Type", "").lower()
                    if ext not in allow_ext and not ct.startswith(allow_ct_prefix):
                        print(f"⚠️ 非允许类型 ext={ext} ct={ct}，跳过")
                        continue
                    save_path = os.path.join(save_dir, fname)
                    with open(save_path, "wb") as f:
                        for chunk in dresp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    print(f"✅ 云附件下载成功: {save_path}")
                    return save_path

            return None



if __name__ == "__main__":
    email_config_path = Path(__file__).parent.parent / 'config' / 'email.yaml'
    email_downloader = EmailDownloader(email_config_path)
    # email_downloader._connect()
    email_downloader.sync_emalls_to_db()
    # print(email_downloader.sync_emalls_to_db())

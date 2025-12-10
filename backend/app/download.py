'''
Author: suntututut wuyaosantu@qq.com
Date: 2025-12-10 15:32:02
LastEditors: suntututut wuyaosantu@qq.com
LastEditTime: 2025-12-10 16:46:00
FilePath: /AutoEmail/backend/app/download.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''




from imap_tools import MailBox
from pathlib import Path

from utils import load_config

class EmailDownloader:
    def __init__(self, config_path: Path):

        self.config = load_config(config_path)

        self.mailbox = MailBox(self.config['imap_server']).login(self.config['username'], self.config['imap_password'])

        self._is_connected = False

        # 允许下载的扩展名白名单
        self.allowed_extensions = {'.pdf', '.docx', '.doc', '.jpg', '.png'}


    def _connect(self):
        if not self._is_connected:
            self.mailbox = MailBox(self.config['imap_server']).login(self.config['username'], self.config['imap_password'])
            print("Connected to the email server")
            self._is_connected = True

    def _disconnect(self):
        if self._is_connected:
            self.mailbox.logout()
            print("Disconnected from the email server")
            self._is_connected = False







if __name__ == "__main__":
    email_config_path = Path(__file__).parent.parent / 'config' / 'email.yaml'
    email_downloader = EmailDownloader(email_config_path)
    email_downloader._connect()

'''
Author: suntututut wuyaosantu@qq.com
Date: 2025-12-10 16:12:14
LastEditors: suntututut wuyaosantu@qq.com
LastEditTime: 2025-12-10 16:16:35
FilePath: /AutoEmail/backend/app/utils.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import yaml
from pathlib import Path

config_path = Path(__file__).parent.parent / 'config' / 'email.yaml'



def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)



if __name__ == "__main__":

    email_config_path = Path(__file__).parent.parent / 'config' / 'email.yaml'
    email_config = load_config(email_config_path)
    print(email_config)
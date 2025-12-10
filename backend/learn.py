'''
Author: suntututut wuyaosantu@qq.com
Date: 2025-12-10 15:16:05
LastEditors: suntututut wuyaosantu@qq.com
LastEditTime: 2025-12-10 15:26:19
FilePath: /AutoEmail/backend/learn.py
Description: 
'''


from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
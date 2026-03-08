import subprocess
import sys
import os

# 【第一順位：強迫安裝】在任何程式啟動前，現場執行安裝指令
def install_and_run():
    # 這裡強迫安裝所有缺少的零件
    pkgs = ["yfinance", "pandas", "pytz", "streamlit-autorefresh", "altair"]
    subprocess.check_call([sys.executable, "-m", "pip", "install", *pkgs])
    
    # 解決 Descriptors 報錯
    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# 執行安裝
try:
    install_and_run()
except:
    pass

# --- 以下才是真正的程式碼 ---
import streamlit as st
import yfinance as yf
# ... (後面維持原樣)

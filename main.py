import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pytz

# 設定台灣時區
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=5000, key="tmf_step1")

st.title("TMF 3分K 監控 - 第一步：連線測試")

# 1. 放置輸入框
user_token = st.text_input("請在此貼上你的 FinMind Token", type="password")

if user_token:
    api = DataLoader()
    api.login_token(user_token) # eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4    
    try:
        # 嘗試抓取 TMF
        now_date = datetime.now(tw_tz).strftime('%Y-%m-%d')
        df = api.taiwan_futures_tick(futures_id="TMF", date=now_date)
        
        if df is not None and not df.empty:
            st.success("✅ 鑰匙有效！已成功連線並抓取數據。")
            st.write("這是最新的成交資料：")
            st.dataframe(df.tail(5))
            st.info("既然連線通了，請告訴我，我再幫你把『紅綠燈』接上去。")
        else:
            st.warning("⚠️ 鑰匙對了，但目前 TMF 沒資料（可能是非盤中）。")
            
    except Exception as e:
        st.error(f"❌ 鑰匙好像有問題: {e}")
else:
    st.info("👈 請先去官網拿 Token 並貼在上方框框內。")

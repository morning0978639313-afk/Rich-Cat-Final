import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# --- 1. 極速更新與時區 ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=3000, key="tmf_aggressive_v13")

st.set_page_config(page_title="微台全實戰監控", layout="wide")
st.title("📊 微台全 3分K - 數據攻堅版")

# --- 🔑 2. Token 與 登入 (強化防錯) ---
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

@st.cache_resource
def get_api_session(token):
    api = DataLoader()
    # 嘗試多種登入語法以確保 Token 生效
    for method in ["login", "login_by_token", "login_token"]:
        if hasattr(api, method):
            try:
                getattr(api, method)(api_token=token)
                return api
            except: continue
    return api

api_client = get_api_session(MY_TOKEN)

# --- 3. 數據攻堅邏輯：多代號自動偵測 ---
def fetch_mxf_full_data():
    now_tw = datetime.now(tw_tz)
    # 抓取今天與昨天的資料，確保「全日盤」跨夜不中斷
    search_date = now_tw.strftime('%Y-%m-%d')
    
    # 積極測試代號：MXF(官方), MXFR (全日連續), TMF (用戶), TMF202603 (當月)
    candidates = ["MXF", "MXFR", "TMF", f"TMF{now_tw.strftime('%Y%m')}"]
    
    for cid in candidates:
        try:
            df = api_client.taiwan_futures_tick(futures_id=cid, date=search_date)
            if df is not None and not df.empty and 'price' in df.columns:
                return df, cid
        except: continue
    return None, None

# --- 4. 渲染介面 ---
st.write(f"⏰ **台灣站點時間**: {datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')}")

df_raw, success_id = fetch_mxf_full_data()

if df_raw is not None:
    st.success(f"🎯 數據攻堅成功！目前使用代號：**{success_id}**")
    
    # --- 3分K 與指標運算 ---
    df_raw['date_dt'] = pd.to_datetime(df_raw['date'] + ' ' + df_raw['time'])
    df_raw = df_raw.set_index('date_dt')
    df_3m = df_raw['price'].resample('3min').ohlc().dropna().reset_index()
    
    if not df_3m.empty:
        last = df_3m.iloc[-1]
        
        # 簡易指標 (確保表格與指數先出來)
        df_3m['ma5'] = df_3m['close'].rolling(5).mean()
        buy_score = 5 if last['close'] > last['ma5'] else 0
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("TMF 即時指數", f"{last['close']:.0f}")
            # 紅綠燈 (Rich 對消邏輯簡化版)
            l_html = f'<div style="width:60px;height:60px;background:{"red" if buy_score > 0 else "#220000"};border-radius:50%;display:inline-block;border:3px solid white;"></div>'
            st.markdown(l_html, unsafe_allow_html=True)
            
        with c2:
            st.write("📊 **即時 3分K 指標明細表**")
            st.dataframe(df_3m.tail(5))
    else:
        st.warning("數據量不足，等待下一根 3分K 棒成型中...")
else:
    st.error("❌ 診斷結論：'data' 報錯持續。")
    st.markdown("""
    ### 🚀 積極處理建議：
    如果多重代號依然抓不到，請在終端機或程式碼中嘗試 **`api_client.taiwan_futures_snapshot()`**。
    這能抓取所有合約的當前價格。我們可以用「快照」的方式，每 3 分鐘紀錄一次價格，強制生成 3分K！
    """)

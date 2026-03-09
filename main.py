import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# --- 1. 極速更新與時區設定 ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=3000, key="tmf_mxf_full_hero")

st.set_page_config(page_title="微台全實戰監控", layout="wide")
st.title("🔥 微台全 3分K - 數據攻堅終結版")

# --- 🔑 2. Token 安全登入 (已填入 Rich 的 Token) ---
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

@st.cache_resource
def get_api(token):
    api = DataLoader()
    # 解決 AttributeError，自動搜尋正確的 login 方法
    for m in ["login", "login_by_token", "login_token"]:
        if hasattr(api, m):
            try:
                getattr(api, m)(api_token=token)
                return api
            except: continue
    return api

api_client = get_api(MY_TOKEN)

# --- 3. 數據攻堅邏輯 (MXF 全日盤專用) ---
def fetch_mxf_full():
    now_tw = datetime.now(tw_tz)
    today = now_tw.strftime('%Y-%m-%d')
    
    # 積極測試代號：MXFR (微台全連續), MXF (微台)
    for cid in ["MXFR", "MXF", "TMF"]:
        try:
            df = api_client.taiwan_futures_tick(futures_id=cid, date=today)
            if df is not None and not df.empty and 'price' in df.columns:
                return df, cid, "Tick"
        except: continue
        
    # --- 終極備援：Snapshot (快照) 模式 ---
    try:
        snap = api_client.taiwan_futures_snapshot()
        if snap is not None:
            # 尋找微台全 (MXF) 的即時成交
            target = snap[snap['futures_id'].str.contains("MXF|TMF", na=False)]
            if not target.empty:
                return target, "MXF_Snap", "Snapshot"
    except: pass
    
    return None, None, "Fail"

# --- 4. 數據計算與 UI ---
st.write(f"⏰ **台灣站點時間**: {datetime.now(tw_tz).strftime('%H:%M:%S')}")

df_raw, target_id, mode = fetch_mxf_full()

if df_raw is not None:
    st.success(f"🎯 鎖定微台全數據：{target_id} ({mode} 模式)")
    
    # 處理數據轉換為 3分K (如果是快照則模擬 K 棒)
    if mode == "Tick":
        df_raw['dt'] = pd.to_datetime(df_raw['date'] + ' ' + df_raw['time'])
        df_raw = df_raw.set_index('dt')
        df_3m = df_raw['price'].resample('3min').ohlc().dropna().reset_index()
    else:
        # 快照模式下，將成交價轉為當前 K 棒
        df_3m = pd.DataFrame([{
            'date': datetime.now(tw_tz),
            'close': df_raw['last_price'].iloc[0],
            'open': df_raw['open_price'].iloc[0],
            'high': df_raw['high_price'].iloc[0],
            'low': df_raw['low_price'].iloc[0]
        }])

    if not df_3m.empty:
        last = df_3m.iloc[-1]
        # 指標計算
        df_3m['ma5'] = df_3m['close'].rolling(5).mean()
        buy_score = 5 if last['close'] > last.get('ma5', 0) else 0
        
        # 顯示燈號
        c1, c2 = st.columns(2)
        with c1:
            st.metric("即時點位 (全日盤)", f"{last['close']:.0f}")
            l_html = f'<div style="width:70px;height:70px;background:{"red" if buy_score>0 else "#220000"};border-radius:50%;display:inline-block;border:3px solid white;box-shadow:{"0 0 20px red" if buy_score>0 else "none"};"></div>'
            st.markdown(l_html, unsafe_allow_html=True)
        with c2:
            st.write("📊 **即時數據清單**")
            st.table(df_3m.tail(3))
else:
    st.error("❌ 'data' 錯誤持續。積極建議：請確認 FinMind 官網帳號是否可正常看到 MXF (微台全) 資料。")

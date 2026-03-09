import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# --- 1. 時區與自動重整 (3秒) ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=3000, key="tmf_aggresive_v12")

st.set_page_config(page_title="微台全實戰監控", layout="wide")
st.title("📊 微台全 3分K - 數據攻堅診斷版")

# --- 2. 🔑 Token 登入 (強化防錯) ---
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

@st.cache_resource
def get_api(token):
    api = DataLoader()
    for method in ["login", "login_by_token", "login_token"]:
        if hasattr(api, method):
            try:
                getattr(api, method)(api_token=token)
                return api
            except: continue
    return api

api_client = get_api(MY_TOKEN)

# --- 3. 數據攻堅抓取邏輯 ---
def fetch_best_data():
    now_tw = datetime.now(tw_tz)
    today = now_tw.strftime('%Y-%m-%d')
    
    # 測試候選代號：TMF, TMF202603 (當月), TMF+當月(簡寫)
    candidates = ["TMF", f"TMF{now_tw.strftime('%Y%m')}", "MXF"] 
    
    for cid in candidates:
        try:
            df = api_client.taiwan_futures_tick(futures_id=cid, date=today)
            if df is not None and not df.empty and 'price' in df.columns:
                return df, cid, "Tick 模式"
        except: continue
        
    # --- 備援計畫：如果 Tick 抓不到，改抓 Snapshot (快照) ---
    try:
        snap = api_client.taiwan_futures_snapshot()
        if snap is not None:
            # 尋找微台全相關資料
            tmf_snap = snap[snap['futures_id'].str.contains("TMF", na=False)]
            if not tmf_snap.empty:
                return tmf_snap, "TMF_Snapshot", "Snapshot 模式"
    except: pass
    
    return None, None, "所有代號連線失敗"

# --- 4. 運算與渲染 ---
st.write(f"⏰ **台灣站點時間**: {datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')}")

data_df, target_id, mode = fetch_best_data()

if data_df is not None:
    st.success(f"🎯 成功鎖定數據源！代號：{target_id} | 模式：{mode}")
    
    # 指標運算 (簡化 3分K 確保表格一定出得來)
    if 'date' in data_df.columns and 'price' in data_df.columns:
        data_df['date_dt'] = pd.to_datetime(data_df['date'] + ' ' + data_df['time'])
        data_df = data_df.set_index('date_dt')
        df_3m = data_df['price'].resample('3min').ohlc().dropna().reset_index()
        
        if not df_3m.empty:
            last = df_3m.iloc[-1]
            # 燈號渲染 (對消邏輯)
            r_cnt = 1 if last['close'] > df_3m['close'].mean() else 0
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("即時點位", f"{last['close']:.0f}")
                # 燈號
                l_html = "".join([f'<div style="width:60px;height:60px;background:{"red" if i<r_cnt else "#220000"};border-radius:50%;display:inline-block;margin:5px;border:2px solid white;"></div>' for i in range(3)])
                st.markdown(l_html, unsafe_allow_html=True)
            with c2:
                st.write("### 數據明細")
                st.dataframe(df_3m.tail(5))
        else:
            st.warning("⚠️ 取得原始資料但無法轉換為 3分K，資料量可能不足。")
    else:
        st.write("快照原始數據：")
        st.dataframe(data_df)
else:
    st.error("❌ 診斷結論：'data' 報錯持續。這代表你的 Token 權限在 FinMind 端可能被限制抓取夜盤 Tick。")
    st.info("💡 解決建議：請嘗試在程式碼中將 futures_id 直接指定為 MTX (小台全) 測試看看資料流是否暢通。")

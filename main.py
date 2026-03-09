import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pytz

# --- 1. 環境設定 ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=5000, key="tmf_token_fix") # 有 Token 後建議 5 秒刷一次最穩

st.set_page_config(page_title="TMF 監控 - 實戰版", layout="wide")
st.title("TMF 3分K 監控 - Token 驗證版")

# --- 2. Token 輸入區 ---
user_token = st.text_input("請輸入你的 FinMind Token (留空則使用免費模式)", type="password")

# --- 3. 數據抓取函式 (修正登入邏輯) ---
@st.cache_data(ttl=5)
def get_tmf_data_with_token(token):import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pytz

# --- 1. 環境設定 ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=5000, key="tmf_token_fix") # 有 Token 後建議 5 秒刷一次最穩

st.set_page_config(page_title="TMF 監控 - 實戰版", layout="wide")
st.title("TMF 3分K 監控 - Token 驗證版")

# --- 2. Token 輸入區 ---
user_token = st.text_input("請輸入你的 FinMind Token (留空則使用免費模式)", type="password")

# --- 3. 數據抓取函式 (修正登入邏輯) ---
@st.cache_data(ttl=5)
def get_tmf_data_with_token(token):
    api = DataLoader()
    if token:
        try:
            # 💡 修正點：正確的登入指令是 login，參數是 api_token
            api.login(api_token=token)
        except Exception as e:
            st.error(f"Token 登入失敗: {e}")
    
    now_tw = datetime.now(tw_tz)
    try:
        # 抓取 TMF (微台全)
        df = api.taiwan_futures_tick(futures_id="TMF", date=now_tw.strftime('%Y-%m-%d'))
        return df
    except Exception as e:
        return f"數據抓取失敗: {e}"

# --- 4. 介面渲染 ---
now_str = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.write(f"⏰ **台灣站點時間**: {now_str}")

res = get_tmf_data_with_token(user_token)

if isinstance(res, str):
    st.warning(f"📡 狀態提示: {res}")
    # 這裡可以呼叫我們先前的 render_lights(0, 0, 0, 0) 畫出空燈號
elif res is not None and not res.empty:
    st.success(f"✅ Token 驗證成功！已抓取 {len(res)} 筆即時數據。")
    st.dataframe(res.tail(5))
    # 接下來就是跑 3分K 與 40 個指標的邏輯...
else:
    st.info("⌛ 等待數據中... 請確認 TMF 目前是否有交易。")    api = DataLoader()
    if token:
        try:
            # 💡 修正點：正確的登入指令是 login，參數是 api_token
            api.login(api_token=token)
        except Exception as e:
            st.error(f"Token 登入失敗: {e}")
    
    now_tw = datetime.now(tw_tz)
    try:
        # 抓取 TMF (微台全)
        df = api.taiwan_futures_tick(futures_id="TMF", date=now_tw.strftime('%Y-%m-%d'))
        return df
    except Exception as e:
        return f"數據抓取失敗: {e}"

# --- 4. 介面渲染 ---
now_str = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.write(f"⏰ **台灣站點時間**: {now_str}")

res = get_tmf_data_with_token(user_token)

if isinstance(res, str):
    st.warning(f"📡 狀態提示: {res}")
    # 這裡可以呼叫我們先前的 render_lights(0, 0, 0, 0) 畫出空燈號
elif res is not None and not res.empty:
    st.success(f"✅ Token 驗證成功！已抓取 {len(res)} 筆即時數據。")
    st.dataframe(res.tail(5))
    # 接下來就是跑 3分K 與 40 個指標的邏輯...
else:
    st.info("⌛ 等待數據中... 請確認 TMF 目前是否有交易。")

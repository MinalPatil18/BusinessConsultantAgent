import streamlit as st
import requests
from stockapp import stock_ui
from businessapp import business_ui

BASE_URL = "http://127.0.0.1:8001"

st.set_page_config(page_title="Business AI Platform", layout="wide")

# ---------- SESSION ----------
defaults = {
    "token": None,
    "chat_id": None,
    "messages": [],
    "page": "login",
    "chat_list": [],
    "app": "chat"
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------- LOAD ----------
def load_chats():
    h = {"Authorization": f"Bearer {st.session_state.token}"}
    r = requests.get(f"{BASE_URL}/get_chats", headers=h)
    if r.status_code == 200:
        st.session_state.chat_list = r.json().get("chats", [])

def load_messages(cid):
    h = {"Authorization": f"Bearer {st.session_state.token}"}
    r = requests.get(
        f"{BASE_URL}/get_messages",
        params={"chat_id": cid},
        headers=h
    )
    if r.status_code == 200:
        st.session_state.messages = r.json().get("messages", [])

# ---------- LOGIN ----------
def login():
    st.title("🤖 Business AI Platform")

    u = st.text_input("Username", key="login_user")
    p = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login", key="login_btn"):
        r = requests.post(f"{BASE_URL}/login",
                          json={"username": u, "password": p})

        if r.status_code == 200:
            st.session_state.token = r.json()["token"]

            h = {"Authorization": f"Bearer {st.session_state.token}"}
            chat = requests.post(f"{BASE_URL}/new_chat", headers=h)

            st.session_state.chat_id = chat.json()["chat_id"]

            load_chats()
            load_messages(st.session_state.chat_id)

            st.session_state.page = "chat"
            st.rerun()
        else:
            st.error("Invalid credentials")

    if st.button("Register", key="goto_register"):
        st.session_state.page = "register"
        st.rerun()

# ---------- REGISTER ----------
def register():
    st.title("Create Account")

    u = st.text_input("Username", key="reg_user")
    p = st.text_input("Password", type="password", key="reg_pass")

    if st.button("Register", key="register_btn"):
        r = requests.post(f"{BASE_URL}/register",
                          json={"username": u, "password": p})

        if r.status_code == 200:
            st.success("Registered successfully")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("User exists")

# ---------- SIDEBAR ----------
def sidebar():
    st.sidebar.title("⚡ Business AI")

    # Apps
    if st.sidebar.button("💬 Chat", key="app_chat"):
        st.session_state.app = "chat"

    if st.sidebar.button("📊 Stock Analyzer", key="app_stock"):
        st.session_state.app = "stock"

    if st.sidebar.button("💼 Business Toolkit", key="app_business"):
        st.session_state.app = "business"

    st.sidebar.markdown("---")

    # New Chat
    if st.sidebar.button("➕ New Chat", key="new_chat"):
        h = {"Authorization": f"Bearer {st.session_state.token}"}
        chat = requests.post(f"{BASE_URL}/new_chat", headers=h)

        if chat.status_code == 200:
            st.session_state.chat_id = chat.json()["chat_id"]
            st.session_state.messages = []
            load_chats()
            st.rerun()

    # History
    st.sidebar.markdown("### 🧠 History")

    for c in st.session_state.chat_list:
        col1, col2 = st.sidebar.columns([4,1])

        with col1:
            if st.button(c["title"], key=f"open_{c['chat_id']}"):
                st.session_state.chat_id = c["chat_id"]
                load_messages(c["chat_id"])

        with col2:
            if st.button("❌", key=f"del_{c['chat_id']}"):
                h = {"Authorization": f"Bearer {st.session_state.token}"}

                requests.delete(
                    f"{BASE_URL}/delete_chat",
                    params={"chat_id": c["chat_id"]},
                    headers=h
                )

                load_chats()
                st.rerun()

    st.sidebar.markdown("---")

    # Logout
    if st.sidebar.button("🚪 Logout", key="logout"):
        st.session_state.token = None
        st.session_state.page = "login"
        st.rerun()

# ---------- CHAT ----------
def chat():
    st.title("💬 Business AI Assistant")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt = st.chat_input("Ask anything about business...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        h = {"Authorization": f"Bearer {st.session_state.token}"}

        r = requests.post(
            f"{BASE_URL}/chat",
            json={"question": prompt, "chat_id": st.session_state.chat_id},
            headers=h
        )

        answer = r.json().get("answer", "Error")

        st.session_state.messages.append({"role": "assistant", "content": answer})

        load_chats()
        st.rerun()

# ---------- ROUTER ----------
if not st.session_state.token:
    st.session_state.page = "login"

if st.session_state.page == "login":
    login()

elif st.session_state.page == "register":
    register()

else:
    sidebar()

    if st.session_state.app == "chat":
        chat()

    elif st.session_state.app == "stock":
        stock_ui()

    elif st.session_state.app == "business":
        business_ui()
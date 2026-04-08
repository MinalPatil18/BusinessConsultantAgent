from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, uuid, os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DB ----------------
conn = sqlite3.connect("app.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    token TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    chat_id TEXT,
    role TEXT,
    content TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_titles (
    chat_id TEXT PRIMARY KEY,
    username TEXT,
    title TEXT
)
""")

conn.commit()

# ---------------- MODELS ----------------
class User(BaseModel):
    username: str
    password: str

class Query(BaseModel):
    question: str
    chat_id: str

# ---------------- AUTH ----------------
def verify_token(token: Optional[str]):
    if not token:
        raise HTTPException(status_code=401, detail="Token missing")

    cursor.execute("SELECT username FROM users WHERE token=?", (token,))
    res = cursor.fetchone()

    if not res:
        raise HTTPException(status_code=401, detail="Invalid token")

    return res[0]

# ---------------- AUTH APIs ----------------
@app.post("/register")
def register(user: User):
    cursor.execute("SELECT * FROM users WHERE username=?", (user.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="User exists")

    cursor.execute("INSERT INTO users (username, password, token) VALUES (?, ?, ?)",
                   (user.username, user.password, ""))
    conn.commit()
    return {"message": "Registered"}

@app.post("/login")
def login(user: User):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                   (user.username, user.password))

    if not cursor.fetchone():
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = str(uuid.uuid4())
    cursor.execute("UPDATE users SET token=? WHERE username=?", (token, user.username))
    conn.commit()

    return {"token": token}

# ---------------- GROQ ----------------
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

# ---------------- TITLE ----------------
def generate_title(text):
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Generate a short 3-5 word title"},
                {"role": "user", "content": text}
            ]
        )
        return res.choices[0].message.content.strip()
    except:
        return text[:30]

# ---------------- CHAT ----------------
@app.post("/chat")
def chat(query: Query, authorization: Optional[str] = Header(None)):
    try:
        token = authorization.replace("Bearer ", "") if authorization else None
        username = verify_token(token)

        user_input = query.question.strip()

        try:
            res = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Business assistant. Answer clearly with links."},
                    {"role": "user", "content": user_input}
                ]
            )
            answer = res.choices[0].message.content
        except Exception as e:
            answer = f"⚠️ AI error: {str(e)}"

        # SAVE CHAT
        cursor.execute(
            "INSERT INTO chats (username, chat_id, role, content) VALUES (?, ?, ?, ?)",
            (username, query.chat_id, "user", user_input)
        )

        cursor.execute(
            "INSERT INTO chats (username, chat_id, role, content) VALUES (?, ?, ?, ?)",
            (username, query.chat_id, "assistant", answer)
        )

        # SAVE TITLE
        cursor.execute("SELECT * FROM chat_titles WHERE chat_id=?", (query.chat_id,))
        if not cursor.fetchone():
            title = generate_title(user_input)
            cursor.execute(
                "INSERT INTO chat_titles (chat_id, username, title) VALUES (?, ?, ?)",
                (query.chat_id, username, title)
            )

        conn.commit()

        return {"answer": answer}

    except Exception as e:
        return {"answer": f"❌ Server error: {str(e)}"}

# ---------------- NEW CHAT ----------------
@app.post("/new_chat")
def new_chat(authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    verify_token(token)
    return {"chat_id": str(uuid.uuid4())}

# ---------------- GET CHATS ----------------
@app.get("/get_chats")
def get_chats(authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    username = verify_token(token)

    cursor.execute("SELECT chat_id, title FROM chat_titles WHERE username=?", (username,))
    rows = cursor.fetchall()

    return {"chats": [{"chat_id": r[0], "title": r[1]} for r in rows]}

# ---------------- GET MESSAGES ----------------
@app.get("/get_messages")
def get_messages(chat_id: str, authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    username = verify_token(token)

    cursor.execute(
        "SELECT role, content FROM chats WHERE chat_id=? AND username=?",
        (chat_id, username)
    )

    rows = cursor.fetchall()

    return {"messages": [{"role": r, "content": c} for r, c in rows]}

@app.delete("/delete_chat")
def delete_chat(chat_id: str, authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "")
    username = verify_token(token)

    cursor.execute("DELETE FROM chats WHERE chat_id=? AND username=?", (chat_id, username))
    cursor.execute("DELETE FROM chat_titles WHERE chat_id=? AND username=?", (chat_id, username))

    conn.commit()

    return {"message": "Chat deleted"}
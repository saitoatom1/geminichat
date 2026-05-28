import os
import sqlite3

from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# =========================
# Gemini API
# =========================
genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")

# =========================
# SQLite
# =========================
conn = sqlite3.connect("chat.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT,
    content TEXT
)
""")

conn.commit()

# =========================
# DB操作
# =========================
def save_message(role, content):
    cursor.execute(
        "INSERT INTO messages (role, content) VALUES (?, ?)",
        (role, content)
    )
    conn.commit()


def load_messages():
    cursor.execute(
        "SELECT role, content FROM messages ORDER BY id ASC"
    )
    return cursor.fetchall()


def clear_messages():
    cursor.execute("DELETE FROM messages")
    conn.commit()

# =========================
# AI生成
# =========================
def generate_ai_response(user_message):

    messages = load_messages()

    prompt = """
あなたは自然で親しみやすいAIアシスタントです。
雑談にも自然に答えてください。
"""

    for role, content in messages:
        if role == "user":
            prompt += f"ユーザー: {content}\n"
        else:
            prompt += f"AI: {content}\n"

    prompt += f"ユーザー: {user_message}\nAI:"

    response = model.generate_content(prompt)

    return response.text

# =========================
# メイン画面
# =========================
@app.route("/")
def home():

    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Gemini Chat</title>

<style>


body {

    /* ★ここ復活（背景画像） */
    background-image: url('/static/bg.jpg');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
    background-margin: 0;
    background-padding: 0;
    background-width: 100%;
    background-height: 100%;

    font-family: Arial;
    max-width: 900px;
    margin: auto;

}

#chat {
    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    height: 350px;
    overflow-y: auto;
    padding: 20px;
    border-radius: 10px;
}

.user {
    background: #dbeafe;
    padding: 10px;
    border-radius: 10px;
    margin: 10px 0;
    white-space: pre-wrap;
}

.ai {
    background: #e5e7eb;
    padding: 10px;
    border-radius: 10px;
    margin: 10px 0;
    white-space: pre-wrap;
}

#message {
    width: 80%;
    padding: 10px;
    font-size: 16px;
}

button {
    padding: 10px;
}


h1 {
    color: rgba(255,255,255,0.75);
    text-align: center;

    /* ガラスっぽい光 */
    text-shadow:
        0 0 8px rgba(255,255,255,0.35),
        0 0 18px rgba(255,255,255,0.25);

    /* ガラス感（軽い透過） */
    backdrop-filter: blur(6px);
    display: inline-block;

    padding: 6px 16px;
    border-radius: 12px;

    border: 1px solid rgba(255,255,255,0.12);

    letter-spacing: 2px;
}
#h1 {   
    color: white;
    text-align: center;
    text-shadow: 2px 2px 10px black;
}
</style>

</head>

<body>

<h1>Sumire AI Chat</h1>

<div id="chat"></div>

<br>

<input type="text" id="message" placeholder="メッセージを入力">

<button onclick="sendMessage()">送信</button>
<button onclick="clearChat()">履歴削除</button>

<script>

window.onload = async function () {
    const res = await fetch("/history")
    const data = await res.json()

    data.forEach(([role, content]) => {
        addMessage(role === "user" ? "あなた" : "Gemini", content, role === "user" ? "user" : "ai")
    })
}

async function sendMessage() {

    const input = document.getElementById("message")
    const message = input.value

    if (!message) return

    addMessage("あなた", message, "user")

    input.value = ""

    const response = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message})
    })

    const data = await response.json()

    addMessage("Gemini", data.reply, "ai")
}

function addMessage(sender, text, className) {

    const chat = document.getElementById("chat")

    const div = document.createElement("div")

    div.className = className

    div.innerHTML = "<b>" + sender + "</b><br>" + text

    chat.appendChild(div)

    chat.scrollTop = chat.scrollHeight
}

async function clearChat() {

    await fetch("/clear", {method: "POST"})

    document.getElementById("chat").innerHTML = ""
}

document.getElementById("message")
.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        sendMessage()
    }
})

</script>

</body>
</html>
"""

# =========================
# API
# =========================
@app.route("/chat", methods=["POST"])
def chat():

    data = request.json
    user_message = data["message"]

    save_message("user", user_message)

    ai_message = generate_ai_response(user_message)

    save_message("assistant", ai_message)

    return jsonify({"reply": ai_message})


@app.route("/history")
def history():
    return jsonify(load_messages())


@app.route("/clear", methods=["POST"])
def clear():
    clear_messages()
    return jsonify({"status": "ok"})


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
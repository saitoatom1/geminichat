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
<html lang="ja">

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Sumire AI Chat</title>

<style>

*{
    box-sizing:border-box;
}

body {

    margin:0;
    padding:0;

    font-family: Arial, sans-serif;

    background-image: url('/static/bg.jpg');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;

    min-height:100vh;

    display:flex;
    justify-content:center;
    align-items:center;

    color:white;
}

.container {

    width:100%;
    max-width:700px;

    padding:15px;
}

.chat-box {

    background: rgba(255,255,255,0.12);

    backdrop-filter: blur(12px);

    border:1px solid rgba(255,255,255,0.15);

    border-radius:20px;

    padding:20px;

    box-shadow:
        0 8px 32px rgba(0,0,0,0.25);

}

h1 {

    text-align:center;

    margin-top:0;

    margin-bottom:20px;

    font-size:32px;

    font-weight:bold;

    color: rgba(255,255,255,0.92);

    text-shadow:
        0 0 10px rgba(255,255,255,0.25),
        0 0 20px rgba(255,255,255,0.15);
}

#chat {

    height:60vh;

    overflow-y:auto;

    padding:10px;

    border-radius:15px;

    background: rgba(0,0,0,0.12);

    margin-bottom:15px;

    scroll-behavior:smooth;
}

.message {

    margin:12px 0;

    padding:14px;

    border-radius:15px;

    line-height:1.6;

    white-space:pre-wrap;

    word-wrap:break-word;

    animation:fadeIn 0.25s ease;
}

.user {

    background:#2563eb;

    margin-left:15%;

    color:white;
}

.ai {

    background:rgba(255,255,255,0.18);

    margin-right:15%;

    color:white;
}

.sender {

    font-weight:bold;

    margin-bottom:6px;

    opacity:0.9;
}

.input-area {

    display:flex;

    gap:10px;

    margin-top:10px;
}

#message {

    flex:1;

    padding:14px;

    border:none;

    border-radius:14px;

    outline:none;

    font-size:16px;

    background: rgba(255,255,255,0.18);

    color:white;

    backdrop-filter: blur(8px);
}

#message::placeholder {
    color: rgba(255,255,255,0.7);
}

button {

    border:none;

    border-radius:14px;

    padding:14px 18px;

    cursor:pointer;

    font-size:15px;

    font-weight:bold;

    transition:0.2s;
}

.send-btn {

    background:#2563eb;

    color:white;
}

.send-btn:hover {

    transform:scale(1.03);
}

.clear-btn {

    background:#ef4444;

    color:white;
}

.clear-btn:hover {

    transform:scale(1.03);
}

@keyframes fadeIn {

    from {
        opacity:0;
        transform:translateY(8px);
    }

    to {
        opacity:1;
        transform:translateY(0);
    }
}

/* =========================
   スマホ対応
========================= */

@media (max-width: 768px) {

    body {

        align-items:flex-start;

        padding:10px;
    }

    .container {

        padding:0;

        width:100%;
    }

    .chat-box {

        padding:14px;

        border-radius:16px;
    }

    h1 {

        font-size:24px;
    }

    #chat {

        height:65vh;
    }

    .message {

        font-size:15px;
    }

    .user {

        margin-left:5%;
    }

    .ai {

        margin-right:5%;
    }

    .input-area {

        flex-direction:column;
    }

    button {

        width:100%;
    }
}

</style>

</head>

<body>

<div class="container">

    <div class="chat-box">

        <h1>Sumire AI Chat</h1>

        <div id="chat"></div>

        <div class="input-area">

            <input
                type="text"
                id="message"
                placeholder="メッセージを入力..."
            >

            <button
                class="send-btn"
                onclick="sendMessage()"
            >
                送信
            </button>

            <button
                class="clear-btn"
                onclick="clearChat()"
            >
                履歴削除
            </button>

        </div>

    </div>

</div>

<script>

window.onload = async function () {

    const res = await fetch("/history")

    const data = await res.json()

    data.forEach(([role, content]) => {

        addMessage(
            role === "user" ? "あなた" : "Sumire AI",
            content,
            role === "user" ? "user" : "ai"
        )
    })
}

async function sendMessage() {

    const input = document.getElementById("message")

    const message = input.value.trim()

    if (!message) return

    addMessage("あなた", message, "user")

    input.value = ""

    try {

        const response = await fetch("/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message
            })
        })

        const data = await response.json()

        addMessage("Sumire AI", data.reply, "ai")

    } catch (error) {

        addMessage(
            "System",
            "通信エラーが発生しました",
            "ai"
        )
    }
}

function addMessage(sender, text, className) {

    const chat = document.getElementById("chat")

    const div = document.createElement("div")

    div.className = "message " + className

    div.innerHTML =
        "<div class='sender'>" +
        sender +
        "</div>" +
        text

    chat.appendChild(div)

    chat.scrollTop = chat.scrollHeight
}

async function clearChat() {

    await fetch("/clear", {
        method:"POST"
    })

    document.getElementById("chat").innerHTML = ""
}

document
.getElementById("message")
.addEventListener("keypress", function(event) {

    if (event.key === "Enter") {

        event.preventDefault()

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
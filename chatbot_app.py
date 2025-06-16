from flask import Flask, request, jsonify, render_template, make_response
import openai
from openai import OpenAI 
import sqlite3
from uuid import uuid4
from datetime import datetime
import os

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, "templates"))
#openai.api_key = "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"  

client = OpenAI(
    base_url='https://xiaoai.plus/v1',
    api_key='sk-YgugHSTLsFiY03RlR0hjJ0f38lasZhFeYLS7TYLj14HNhexf'
)

# 替换为新密钥
#print("Template folder:", app.template_folder)

def init_db():
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS conversations
                (id TEXT, prolific_pid TEXT, user_input TEXT, bot_response TEXT, timestamp DATETIME)""")
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    try:
        if not os.path.exists(os.path.join(app.template_folder, 
"GPT_fake.html")):
            return "Error: GPT_fake.html not found"
        response = make_response(render_template("GPT_fake.html"))
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
    except Exception as e:
        return f"Template Error: {str(e)}"

@app.route("/chat", methods=["POST"])
def chat():
    prolific_pid = request.form.get("PROLIFIC_PID") or request.args.get("PROLIFIC_PID")
    user_input = request.form.get("input")
    end_session = request.form.get("end_session")
    print("Received: PROLIFIC_PID=", prolific_pid, ", input=", user_input, ", end_session=", end_session)

    if not prolific_pid:
        return jsonify({"error": "PROLIFIC_PID required"}), 400
    if not user_input and not end_session:
        return jsonify({"error": "input or end_session required"}), 400

    if end_session:
        try:
            conn = sqlite3.connect("conversations.db")
            c = conn.cursor()
            c.execute("INSERT INTO conversations (id, prolific_pid, user_input, bot_response, timestamp) VALUES (?, ?, ?, ?, ?)",
                      (str(uuid4()), prolific_pid, "Session ended", "Completion code generated", datetime.now()))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print("SQLite Error:", str(e))
            return jsonify({"error": "Database error: " + str(e)}), 500
        
        redirect_url = f"https://your.qualtrics.com/jfe/form/SV_XXXXXX?PROLIFIC_PID={prolific_pid}"  # ← 替换成你的问卷后续页面
        return jsonify({
            "response": "Session ended",
            "completion_code": str(uuid4())[:8],
            "redirect_url": redirect_url
        })

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",  # 切换回 4.1-nano
            messages=[{"role": "user", "content": user_input}],
            max_tokens=100
        )
        bot_response = response.choices[0].message.content
    except openai.error.OpenAIError as e:
        print("OpenAI Error:", str(e))
        return jsonify({"error": "OpenAI API failed: " + str(e)}), 500

    try:
        conn = sqlite3.connect("conversations.db")
        c = conn.cursor()
        c.execute("INSERT INTO conversations (id, prolific_pid, user_input, bot_response, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (str(uuid4()), prolific_pid, user_input, bot_response, datetime.now()))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print("SQLite Error:", str(e))
        return jsonify({"error": "Database error: " + str(e)}), 500

    return jsonify({"response": bot_response, "completion_code": None})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


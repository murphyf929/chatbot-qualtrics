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

# This is required to securely store the return_url.
app.secret_key = os.urandom(24)

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
                (id TEXT, prolific_pid TEXT, user_input TEXT, bot_response TEXT, timestamp DATETIME, return_url TEXT)""")
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    try:
        prolific_pid = request.args.get('prolific_id')
        return_url = request.args.get('return_url')

        # Store the return_url in the user's session so we can retrieve it later.
        if return_url:
            session['return_url'] = return_url

        if not os.path.exists(os.path.join(app.template_folder, 
"GPT_fake.html")):
            return "Error: GPT_fake.html not found"
        response = make_response(render_template("GPT_fake.html", prolific_pid=prolific_pid))
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
    except Exception as e:
        return f"Template Error: {str(e)}"

@app.route("/chat", methods=["POST"])
def chat():
    """
    Handles the chat logic. It receives user input and returns the bot's response.
    It does NOT handle the redirection anymore.
    """
    prolific_pid = request.form.get("prolific_pid")
    user_input = request.form.get("input")
    
    if not prolific_pid:
        return jsonify({"error": "PROLIFIC_PID is required"}), 400
    if not user_input:
        return jsonify({"error": "User input is required"}), 400

    try:
        # Get AI response
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": user_input}],
            max_tokens=150
        )
        bot_response = response.choices[0].message.content

        # Log conversation to database
        conn = sqlite3.connect("conversations.db")
        c = conn.cursor()
        c.execute("INSERT INTO conversations (id, prolific_pid, user_input, bot_response, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (str(uuid4()), prolific_pid, user_input, bot_response, datetime.now()))
        conn.commit()
        conn.close()

        return jsonify({"response": bot_response})

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/end_session")
def end_session():
    """
    This new route handles the end of the session.
    It retrieves the return_url from the session and redirects the user.
    """
    # Retrieve the return_url that we stored when the user first arrived.
    return_url = session.get('return_url', 'https://www.prolific.com') # Default to Prolific if URL is somehow lost
    
    # You can add a final log entry if you wish
    # prolific_pid = session.get('prolific_id', 'UNKNOWN')
    # conn = sqlite3.connect("conversations.db")
    # c = conn.cursor()
    # c.execute("INSERT INTO conversations (id, prolific_pid, user_input, bot_response, timestamp) VALUES (?, ?, ?, ?, ?)",
    #           (str(uuid4()), prolific_pid, "Session ended by user", "Redirecting back to Qualtrics", datetime.now()))
    # conn.commit()
    # conn.close()
    
    # Clear the session data
    session.clear()
    
    # Redirect the user's browser back to the Qualtrics survey
    return redirect(return_url)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

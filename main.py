import os
import requests
import json
from flask import Flask, request
from groq import Groq

# --- CREDENCIAIS ---
Z_API_ID = "3EC502952818632B0E31C6B75FFFD411"
Z_API_TOKEN = "43FB843CF98C6CD27D3E0E50"
CLIENT_TOKEN = "F12d5b62bed3f447598b17c727045141cS" 
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
chat_sessions = {}

# Prompt Especialista
PROMPT_SISTEMA = """
Você é Pedro Lima, Especialista Microlins. Responda curto e termine com uma pergunta.
ROTEIRO: 1. Nome > 2. Cidade > 3. Capital > 4. Lucro > 5. Prazo.
"""

@app.route("/", methods=["GET"])
def health(): return "Modo Diagnostico Ativo", 200

def gerar_resposta_ia(phone, msg):
    try:
        if phone not in chat_sessions:
            chat_sessions[phone] = [{"role": "system", "content": PROMPT_SISTEMA}]
        
        chat_sessions[phone].append({"role": "user", "content": msg})

        # Testando Llama 3.3
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_sessions[phone][-6:],
            temperature=0.3
        )
        resp = completion.choices[0].message.content
        chat_sessions[phone].append({"role": "assistant", "content": resp})
        return resp
    except Exception as e:
        print(f"❌ ERRO NA IA (GROQ): {e}", flush=True)
        return "Olá! Sou o Pedro Lima. Com quem eu falo?"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200
    
    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"🔍 1. Recebi do WhatsApp: {msg} | De: {phone}", flush=True)
        
        # Gera resposta
        resp = gerar_resposta_ia(phone, msg)
        print(f"🧠 2. A IA Gerou: {resp}", flush=True)
        
        # Tenta Enviar
        url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        payload = {"phone": phone, "message": resp}
        headers = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        
        try:
            r = requests.post(url, json=payload, headers=headers)
            print(f"🚀 3. STATUS Z-API: {r.status_code}", flush=True)
            print(f"📜 4. RESPOSTA Z-API: {r.text}", flush=True)
        except Exception as e:
            print(f"❌ 5. FALHA CONEXÃO Z-API: {e}", flush=True)

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))


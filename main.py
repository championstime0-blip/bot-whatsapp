import os
import time
import requests
import google.generativeai as genai
from flask import Flask, request

# ==================================================
# CONFIGURAÇÕES
# ==================================================
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

app = Flask(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Memória RAM
chat_sessions = {}

PROMPT_SISTEMA = """
# ROLE: Consultor Pedro Lima.
# OBJETIVO: Qualificar lead.
1. Cidade?
2. Área?
3. Prazo?
4. Capital?
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    # Vamos direto no modelo que apareceu na sua lista, com o prefixo exato
    nome_modelo = "models/gemini-2.0-flash" 

    if phone not in chat_sessions:
        chat_sessions[phone] = {'history': []}

    try:
        print(f"🔄 Tentando conectar no: {nome_modelo}...", flush=True)
        
        model = genai.GenerativeModel(nome_modelo)
        chat = model.start_chat(history=chat_sessions[phone]['history'])
        
        response = chat.send_message(f"Sistema: {PROMPT_SISTEMA}\nLead: {mensagem_usuario}")
        
        chat_sessions[phone]['history'] = chat.history
        return response.text

    except Exception as e:
        erro_tecnico = str(e)
        print(f"❌ ERRO GRAVE: {erro_tecnico}", flush=True)
        # AQUI ESTÁ O SEGREDO: Manda o erro pro WhatsApp para a gente ler
        return f"🚨 ERRO TÉCNICO (Mande print pro suporte): {erro_tecnico}"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe") is True: return "ok", 200

    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"📩 Lead: {msg}", flush=True)
        resp = gerar_resposta_ia(phone, msg)
        
        requests.post(
            f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
            json={"phone": phone, "message": resp}, 
            headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        )
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

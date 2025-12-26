import os
import time
import requests
import google.generativeai as genai
from flask import Flask, request

# CONFIGURAÇÕES
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

app = Flask(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

chat_sessions = {}

PROMPT_SISTEMA = """
# ROLE: Consultor Pedro Lima (Expansão Microlins).
# REGRA: Uma pergunta por vez. Curto e direto.
1. Cidade?
2. Área atual?
3. Prazo (3 meses ou +)?
4. Capital (Investimento 200k)?
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    # ESTRATÉGIA 2025: Usar a versão LITE para ter mais cota gratuita
    modelos_candidatos = [
        "models/gemini-2.0-flash-lite", # <--- MAIOR COTA EM 2025
        "models/gemini-2.0-flash-exp",
        "models/gemini-flash-lite-latest"
    ]

    if phone not in chat_sessions:
        chat_sessions[phone] = {'history': []}
    
    # Limita o histórico para as últimas 6 mensagens (evita erro de memória/tokens)
    if len(chat_sessions[phone]['history']) > 6:
        chat_sessions[phone]['history'] = chat_sessions[phone]['history'][-6:]

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando modelo estável: {nome_modelo}...", flush=True)
            model = genai.GenerativeModel(nome_modelo)
            chat = model.start_chat(history=chat_sessions[phone]['history'])
            
            response = chat.send_message(f"{PROMPT_SISTEMA}\nLead: {mensagem_usuario}")
            
            chat_sessions[phone]['history'] = chat.history
            return response.text

        except Exception as e:
            erro = str(e)
            print(f"❌ Falha no {nome_modelo}: {erro}", flush=True)
            if "429" in erro or "limit" in erro.lower():
                time.sleep(2) # Espera o cooldown do Google
                continue
            continue

    return "Oi! Recebi sua mensagem. Pode me dar um minutinho? Meu sistema de viabilidade está processando os dados de Salvador/região."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe") is True: return "ok", 200

    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"📩 Lead ({phone}): {msg}", flush=True)
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

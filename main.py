import os
import time
import requests
import google.generativeai as genai
from flask import Flask, request

# ==================================================
# 1. CONFIGURAÇÕES
# ==================================================
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

app = Flask(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Memória RAM do Chat
chat_sessions = {}

# ==================================================
# 2. CÉREBRO (IA)
# ==================================================
PROMPT_SISTEMA = """
# ROLE: Consultor Pedro Lima (Expansão Ensina Mais Turma da Mônica).
# OBJETIVO: Qualificar lead para franquia.
# ROTEIRO:
1. PRACA: Cidade e Estado de interesse?
2. ATUACAO: Área de trabalho atual?
3. PRAZO: Interesse para agora (90 dias) ou futuro?
4. CAPITAL: Possui investimento disponível?
# REGRA: Seja curto. Uma pergunta por vez.
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    """
    Estratégia: Prioriza o 1.5 Flash pelo alto limite de quota.
    """
    modelos_candidatos = [
        "gemini-1.5-flash",    # 1º: Alta Quota (1500 req/dia) - O MAIS SEGURO
        "gemini-1.5-pro",      # 2º: Backup Inteligente
        "gemini-2.5-flash"     # 3º: O Novo (Deixamos por último pois o limite é 20)
    ]

    # Inicializa sessão se não existir
    if phone not in chat_sessions:
        chat_sessions[phone] = {'history': []}

    prompt_completo = f"Instrução: {PROMPT_SISTEMA}\n\nLead disse: {mensagem_usuario}"

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando modelo: {nome_modelo}...", flush=True)
            
            model = genai.GenerativeModel(nome_modelo)
            chat = model.start_chat(history=chat_sessions[phone]['history'])
            response = chat.send_message(prompt_completo)
            
            # Atualiza histórico
            chat_sessions[phone]['history'] = chat.history
            return response.text

        except Exception as e:
            erro_str = str(e)
            
            # Tratamento de Quota (429)
            if "429" in erro_str:
                print(f"⏳ Quota cheia no {nome_modelo}. Tentando outro...", flush=True)
                time.sleep(1) # Breve pausa
                continue 
            
            # Tratamento de Modelo não encontrado (404)
            if "404" in erro_str or "not found" in erro_str.lower():
                print(f"⚠️ {nome_modelo} off. Pulando...", flush=True)
                continue
            
            print(f"❌ Erro {nome_modelo}: {erro_str}", flush=True)
            continue

    return "No momento nossos sistemas estão com alto volume. Tente em 1 minuto."

# ==================================================
# 3. WEBHOOK
# ==================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200

    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"📩 Lead: {msg}", flush=True)
        resp = gerar_resposta_ia(phone, msg)
        print(f"🤖 Bot: {resp}", flush=True)
        
        requests.post(
            f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
            json={"phone": phone, "message": resp}, 
            headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        )
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

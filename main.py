import os
import time
import requests
import google.generativeai as genai
from flask import Flask, request

# --- DIAGNÓSTICO DE VERSÃO (VAI APARECER NO LOG) ---
try:
    import importlib.metadata
    versao_lib = importlib.metadata.version("google-generativeai")
    print(f"🛑 VERSÃO REAL INSTALADA: {versao_lib}", flush=True)
except:
    print("🛑 NÃO FOI POSSÍVEL LER A VERSÃO", flush=True)
# ---------------------------------------------------

Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

app = Flask(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

chat_sessions = {}

PROMPT_SISTEMA = """
# ROLE: Consultor Pedro Lima (Expansão Ensina Mais Turma da Mônica).
# OBJETIVO: Qualificar lead.
# ROTEIRO:
1. PRACA: Cidade/Estado?
2. ATUACAO: Área atual?
3. PRAZO: 3 meses ou longo prazo?
4. CAPITAL: Investimento disponível?
# REGRA: Uma pergunta por vez.
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    # LISTA DE EMERGÊNCIA
    # Se o 1.5 falhar, ele vai tentar o "gemini-pro" (1.0) que funciona em versões antigas
    modelos_candidatos = [
        "gemini-1.5-flash",    # O ideal
        "gemini-pro",          # O Clássico (Funciona quase sempre)
        "gemini-1.0-pro"       # Outro nome do Clássico
    ]

    if phone not in chat_sessions:
        chat_sessions[phone] = {'history': []}

    prompt_completo = f"Instrução: {PROMPT_SISTEMA}\n\nLead disse: {mensagem_usuario}"

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando modelo: {nome_modelo}...", flush=True)
            
            model = genai.GenerativeModel(nome_modelo)
            chat = model.start_chat(history=chat_sessions[phone]['history'])
            response = chat.send_message(prompt_completo)
            
            chat_sessions[phone]['history'] = chat.history
            return response.text

        except Exception as e:
            erro_str = str(e)
            
            if "429" in erro_str:
                print(f"⏳ Quota no {nome_modelo}. Pulando...", flush=True)
                time.sleep(1)
                continue 
            
            if "404" in erro_str or "not found" in erro_str.lower():
                print(f"⚠️ {nome_modelo} não encontrado (404). Pulando...", flush=True)
                continue
            
            print(f"❌ Erro {nome_modelo}: {erro_str}", flush=True)
            continue

    return "Sistema em manutenção momentânea. Tente em 1 minuto."

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

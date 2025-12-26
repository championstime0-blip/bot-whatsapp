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

chat_sessions = {}

# ==================================================
# 2. CÉREBRO (IA)
# ==================================================
PROMPT_SISTEMA = """
# ROLE: Consultor Pedro Lima (Expansão Microlins - Grupo MoveEdu).
# OBJETIVO: Qualificar lead para franquia Modelo 2026.
# TONE: Profissional, breve e humano.

# ROTEIRO (Uma pergunta por vez):
1. Cidade de interesse?
2. Área de atuação atual?
3. Prazo de investimento (3 meses ou longo prazo)?
4. Capital disponível (Investimento ~200k)?
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    # ESTRATÉGIA FINAL: Usar os "Aliases" (Apelidos) do Google.
    # "gemini-flash-latest" -> O Google escolhe o melhor Flash disponível para sua conta.
    # "gemini-pro" -> O modelo clássico e estável.
    modelos_candidatos = [
        "gemini-flash-latest", 
        "gemini-pro-latest",
        "gemini-pro"
    ]

    if phone not in chat_sessions:
        chat_sessions[phone] = {'history': []}

    prompt_completo = f"Instrução: {PROMPT_SISTEMA}\n\nLead disse: {mensagem_usuario}"

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando conectar no alias: {nome_modelo}...", flush=True)
            
            # Tenta com o prefixo 'models/' para garantir
            try:
                model = genai.GenerativeModel(f"models/{nome_modelo}")
            except:
                model = genai.GenerativeModel(nome_modelo)

            chat = model.start_chat(history=chat_sessions[phone]['history'])
            response = chat.send_message(prompt_completo)
            
            chat_sessions[phone]['history'] = chat.history
            return response.text

        except Exception as e:
            erro = str(e)
            # Se for erro de Quota (429) ou Limite Zero
            if "429" in erro or "limit" in erro.lower():
                print(f"⏳ {nome_modelo} bloqueado/cheio. Tentando próximo...", flush=True)
                time.sleep(1)
                continue 
            
            if "404" in erro:
                print(f"⚠️ {nome_modelo} não encontrado. Pulando...", flush=True)
                continue
            
            print(f"❌ Erro em {nome_modelo}: {erro}", flush=True)
            continue

    return "No momento nossos sistemas estão em atualização. Tente em 1 minuto."

# ==================================================
# 3. WEBHOOK
# ==================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe") is True: return "ok", 200

    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"📩 Lead: {msg}", flush=True)
        
        # Responde
        resp = gerar_resposta_ia(phone, msg)
        print(f"🤖 Bot: {resp}", flush=True)
        
        try:
            requests.post(
                f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
                json={"phone": phone, "message": resp}, 
                headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
            )
        except Exception as e:
            print(f"❌ Erro Z-API: {e}", flush=True)
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

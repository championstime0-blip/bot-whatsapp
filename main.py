import os
import requests
from flask import Flask, request
from groq import Groq

# --- CREDENCIAIS ATUALIZADAS (CONFORME SUA IMAGEM) ---
Z_API_ID = "3EC502952818632B0E31C6B75FFFD411"
Z_API_TOKEN = "43FB843CF98C6CD27D3E0E50"
CLIENT_TOKEN = "Fecccd92e36ba4bc990f72fb8be200436S" # Verifique se este token continua o mesmo no seu painel
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

chat_sessions = {}

PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor Microlins. Siga este roteiro:
1. ATUAÇÃO: "Legal Sr, em qual área o Sr trabalha aí na sua cidade?"
2. PRAÇA: "O negócio pretende montar aí na sua cidade mesmo?"
3. PRAZO: "Pretende abrir nos próximos 3 meses ou a longo prazo?"
4. LUCRO: "Quanto esse negócio precisa dar de lucro mensal?"
5. CAPITAL: "Qual valor você tem disponível hoje para investir?"
REGRAS: Não repita perguntas. Uma por vez.
"""

@app.route("/", methods=["GET"])
def health(): return "Z-API Corrigida e Online", 200

def gerar_resposta_ia(phone, mensagem_usuario):
    if phone not in chat_sessions:
        chat_sessions[phone] = [{"role": "system", "content": PROMPT_SISTEMA}]
    
    chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=chat_sessions[phone][-8:],
            temperature=0.4,
        )
        resposta = completion.choices[0].message.content
        chat_sessions[phone].append({"role": "assistant", "content": resposta})
        return resposta
    except Exception as e:
        print(f"Erro IA: {e}")
        return "Legal! Me diga, em qual área o Sr trabalha hoje?"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200
    
    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        resp = gerar_resposta_ia(phone, msg)
        
        # Envio corrigido para Z-API
        requests.post(
            f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
            json={"phone": phone, "message": resp}, 
            headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        )
            
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))


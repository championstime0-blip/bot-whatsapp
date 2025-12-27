import os
import requests
from flask import Flask, request
from groq import Groq

# --- CONFIGURAÇÕES ---
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"
# Certifique-se de adicionar esta variável no painel do Render!
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

app = Flask(__name__)

# Inicializa o cliente apenas se a chave existir para evitar erro no boot
client = None
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)

chat_sessions = {}

PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor Microlins. 
Siga este roteiro EXATAMENTE e não repita perguntas.

ROTEIRO:
1. ATUAÇÃO: "Legal Sr, em qual área o Sr trabalha aí na sua cidade?"
2. PRAÇA: "O negócio pretende montar aí na sua cidade mesmo?"
3. PRAZO: "Pretende abrir nos próximos 3 meses ou a longo prazo?"
4. LUCRO: "Quanto esse negócio precisa dar de lucro mensal?"
5. CAPITAL: "Qual valor você tem disponível hoje para investir?"
"""

@app.route("/", methods=["GET"])
def health():
    return "Llama 3.1 Online", 200

def gerar_resposta_ia(phone, mensagem_usuario):
    if not client:
        return "Erro: Chave Groq não configurada."

    if phone not in chat_sessions:
        chat_sessions[phone] = [{"role": "system", "content": PROMPT_SISTEMA}]

    chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})

    try:
        # Llama 3.1 8B via Groq (Ultra rápido)
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=chat_sessions[phone][-6:], # Mantém o contexto curto
            temperature=0.5,
            max_tokens=512,
        )
        
        resposta = completion.choices[0].message.content
        chat_sessions[phone].append({"role": "assistant", "content": resposta})
        return resposta

    except Exception as e:
        print(f"Erro Llama: {e}")
        return "Entendi! E me diga uma coisa, você trabalha em qual área aí na sua cidade hoje?"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200
    
    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        resp = gerar_resposta_ia(phone, msg)
        requests.post(
            f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
            json={"phone": phone, "message": resp}, 
            headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        )
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

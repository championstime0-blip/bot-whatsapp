import os
import requests
from flask import Flask, request
from groq import Groq

# --- DADOS DA SUA IMAGEM ---
Z_API_ID = "3EC502952818632B0E31C6B75FFFD411"
Z_API_TOKEN = "43FB843CF98C6CD27D3E0E50"
CLIENT_TOKEN = "F12d5b62bed3f447598b17c727045141cS" 
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
chat_sessions = {}

# Roteiro solicitado
PROMPT_SISTEMA = """Você é o Pedro Lima, consultor de expansão. 
1º (ÁREA DE ATUAÇÃO) "Legal Sr, e me fala uma coisa, o Sr trabalha ou atua em qual área aí na sua cidade?"
2º (PRAÇA DE INTERESSE) "Ah legal, e me outra coisa, e o negócio pretende montar é aí na sua cidade mesmo?"
3º (PRAZO) "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio ou longo prazo?"
4º (LUCRO) "E me fala uma coisa Sr, esse negócio, pra ser bom para o Sr, ele precisa dar quanto na última linha?"
5º (CAPITAL) "Legal Sr, a lucratividade está ligada ao investimento. Qual valor disponível para investir?"
"""

@app.route("/", methods=["GET"])
def health(): return "OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200
    
    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        # 1. Gerar resposta com Llama 3.1
        if phone not in chat_sessions:
            chat_sessions[phone] = [{"role": "system", "content": PROMPT_SISTEMA}]
        chat_sessions[phone].append({"role": "user", "content": msg})
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=chat_sessions[phone][-6:],
            temperature=0.3
        )
        resp = completion.choices[0].message.content

        # 2. Enviar para Z-API com DEBUG
        zapi_url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        payload = {"phone": phone, "message": resp}
        headers = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        
        try:
            r = requests.post(zapi_url, json=payload, headers=headers, timeout=10)
            print(f"DEBUG Z-API: Status {r.status_code} - Resposta: {r.text}", flush=True)
        except Exception as e:
            print(f"ERRO CONEXAO Z-API: {e}", flush=True)
            
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)


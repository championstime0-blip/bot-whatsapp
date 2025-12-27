import os
import json
import requests
from flask import Flask, request
from google import genai
from google.genai import types

# --- CONFIGURAÇÕES ---
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

app = Flask(__name__)
client = genai.Client(api_key=GEMINI_API_KEY)

# Arquivo para salvar o histórico e não esquecer após reinícios
DB_FILE = "chat_history.json"

def carregar_historico():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def salvar_historico(historico):
    with open(DB_FILE, "w") as f:
        json.dump(historico, f)

PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor de expansão Microlins. 
Analise o histórico para NÃO repetir perguntas já respondidas. 
Siga este roteiro EXATO:
1. ATUAÇÃO: "Legal Sr, em qual área o Sr trabalha aí na sua cidade?"
2. PRAÇA: "O negócio pretende montar aí na sua cidade mesmo?"
3. PRAZO: "Pretende abrir nos próximos 3 meses ou a longo prazo? O que é longo prazo para o Sr?"
4. LUCRO: "Quanto esse negócio precisa dar de lucro livre para ser bom para o Sr?"
5. CAPITAL: "Para ter lucro, precisa investir. Qual valor você tem disponível hoje?"
"""

@app.route("/", methods=["GET"])
def health(): return "Bot Ativo com Memória", 200

def gerar_resposta_ia(phone, mensagem_usuario):
    modelos_fallback = ["gemini-3.0-flash", "gemini-2.0-flash"]
    chat_sessions = carregar_historico()

    if phone not in chat_sessions:
        chat_sessions[phone] = []

    chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})
    
    contents = [
        types.Content(role=m["role"], parts=[types.Part.from_text(text=m["content"])]) 
        for m in chat_sessions[phone][-6:]
    ]

    for modelo in modelos_fallback:
        try:
            response = client.models.generate_content(
                model=modelo,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=PROMPT_SISTEMA, temperature=0.3)
            )
            resposta = response.text
            chat_sessions[phone].append({"role": "model", "content": resposta})
            
            # Salva no arquivo para persistir no reinício do Render
            salvar_historico(chat_sessions)
            return resposta
        except Exception as e:
            if "429" in str(e): continue
            print(f"Erro no {modelo}: {e}")
            continue

    return "Legal Sr! Me diga uma coisa, você trabalha em qual área aí na sua cidade?"

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

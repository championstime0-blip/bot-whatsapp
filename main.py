import os
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

# Memória RAM para o histórico
chat_sessions = {}

# PROCESSO DE SONDAGEM RIGOROSO
PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor de expansão Microlins. 
OBJETIVO: Seguir este roteiro sem repetir perguntas que já constem no histórico.

ROTEIRO DE SONDAGEM:
1. ATUAÇÃO: "Legal Sr, e me fala uma coisa, o Sr trabalha ou atua em qual área aí na sua cidade?"
2. PRAÇA: "Ah legal, e me outra coisa, e o negócio pretende montar é aí na sua cidade mesmo?"
3. PRAZO: "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio ou longo prazo?"
4. LUCRO: "E me fala uma coisa Sr, esse negócio, pra ser bom para o Sr, ele precisa dar quanto na última linha?"
5. CAPITAL: "Legal Sr, para você ter uma ideia, a lucratividade está diretamente ao investimento. Qual valor você tem disponível para investir hoje?"

REGRAS: 
- Analise o histórico e pule o que já foi respondido. 
- Apenas uma pergunta por vez.
"""

@app.route("/", methods=["GET"])
def health(): 
    return "Bot Operacional (Gemini 2.0 Flash)", 200

def gerar_resposta_ia(phone, mensagem_usuario):
    # Usando o modelo estável que NÃO dá erro 404
    MODELO = "gemini-2.0-flash"

    if phone not in chat_sessions:
        chat_sessions[phone] = []

    chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})
    
    # Prepara o histórico (últimas 6 mensagens para manter a conversa leve)
    contents = [
        types.Content(role=m["role"], parts=[types.Part.from_text(text=m["content"])]) 
        for m in chat_sessions[phone][-6:]
    ]

    try:
        response = client.models.generate_content(
            model=MODELO,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=PROMPT_SISTEMA,
                temperature=0.3
            )
        )
        resposta = response.text
        chat_sessions[phone].append({"role": "model", "content": resposta})
        return resposta
    except Exception as e:
        print(f"Erro na API Gemini: {e}", flush=True)
        # Fallback imediato se o 404 ou 429 persistir
        return "Legal! E me diga uma coisa, você trabalha em qual área aí na sua cidade hoje?"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200
    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"📩 Mensagem recebida: {msg}", flush=True)
        resp = gerar_resposta_ia(phone, msg)
        
        requests.post(
            f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
            json={"phone": phone, "message": resp}, 
            headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        )
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

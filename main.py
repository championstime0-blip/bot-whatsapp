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

# PROCESSO DE SONDAGEM SOLICITADO
PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor de expansão. Siga este roteiro EXATAMENTE. 
NÃO repita perguntas já respondidas no histórico.

ROTEIRO:
1º (ÁREA DE ATUAÇÃO) "Legal Sr, e me fala uma coisa, o Sr trabalha ou atua em qual área aí na sua cidade?"
2º (PRAÇA DE INTERESSE) "Ah legal, e me outra coisa, e o negócio pretende montar é aí na sua cidade mesmo?"
3º (PRAZO) "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio ou longo prazo? E o que seria médio ou longo prazo para o Sr?"
4º (LUCRO) "E me fala uma coisa Sr, esse negócio, pra ser bom para o Sr, ele precisa dar quanto na última linha?"
5º (CAPITAL) "Legal Sr, para você ter uma ideia, a lucratividade está diretamente ao investimento. Tem um monte de franquia dizendo que com apenas 10 mil o Sr vai lucrar 50. E isso não é uma verdade. Qual valor você tem disponível para investir hoje?"
"""

@app.route("/", methods=["GET"])
def health(): return "Gemini 3.0 Ativo", 200

def gerar_resposta_ia(phone, mensagem_usuario):
    # O sucessor do 1.5 Flash em 2025
    MODELO = "gemini-3.0-flash-lite"

    if phone not in chat_sessions:
        chat_sessions[phone] = []

    chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})
    
    # Prepara histórico para o Gemini 3.0
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
        print(f"Erro IA: {e}")
        # Fallback para não deixar o lead sem resposta
        return "Legal! E me diga uma coisa, você trabalha em qual área aí na sua cidade hoje?"

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

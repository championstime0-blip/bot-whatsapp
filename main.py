import os
import time
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

# Inicializa o cliente fora da função para ser mais rápido
client = genai.Client(api_key=GEMINI_API_KEY)

# Memória RAM para histórico (Limpa se o Render reiniciar)
chat_sessions = {}

# SEU PROCESSO DE SONDAGEM RÍGIDO
PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor de expansão. 
Siga este roteiro rigorosamente. Analise o histórico e NUNCA repita perguntas já respondidas.

ROTEIRO:
1. (ÁREA DE ATUAÇÃO) "Legal Sr, e me fala uma coisa, o Sr trabalha ou atua em qual área aí na sua cidade?"
2. (PRAÇA DE INTERESSE) "Ah legal, e me outra coisa, e o negócio pretende montar é aí na sua cidade mesmo?"
3. (PRAZO) "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio ou longo prazo? E o que seria médio ou longo prazo para o Sr?"
4. (LUCRO) "E me fala uma coisa Sr, esse negócio, pra ser bom para o Sr, ele precisa dar quanto na última linha?"
5. (CAPITAL) "Legal Sr, para você ter uma ideia, a lucratividade está diretamente ao investimento. Qual valor você tem disponível para investir hoje?"

REGRAS:
- Uma pergunta por vez.
- Se o lead responder a cidade na primeira mensagem, pule para a Área de Atuação.
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    if phone not in chat_sessions:
        chat_sessions[phone] = []

    try:
        # Adiciona a fala do lead
        chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})

        # Monta o histórico para enviar ao Google
        contents = []
        for msg in chat_sessions[phone][-8:]: # Pega as últimas 8 para contexto
            contents.append(types.Content(role=msg["role"], parts=[types.Part.from_text(text=msg["content"])]))

        # Chamada da API 2025
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=PROMPT_SISTEMA,
                temperature=0.5
            )
        )

        resposta_texto = response.text
        chat_sessions[phone].append({"role": "model", "content": resposta_texto})
        return resposta_texto

    except Exception as e:
        print(f"❌ ERRO IA: {e}", flush=True)
        # Se der erro de cota (429), avisa no log
        if "429" in str(e):
            return "Sr, estamos com muitos atendimentos agora. Pode me mandar um 'oi' em 1 minuto?"
        return "Tive uma instabilidade, mas me diga: em qual área o Sr atua hoje?"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200

    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"📩 Lead: {msg}", flush=True)
        resp = gerar_resposta_ia(phone, msg)
        
        # Envio Z-API
        requests.post(
            f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
            json={"phone": phone, "message": resp}, 
            headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        )
            
    return "ok", 200

# O Render precisa que o host seja 0.0.0.0
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

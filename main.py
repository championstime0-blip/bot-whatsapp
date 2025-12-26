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
client = genai.Client(api_key=GEMINI_API_KEY)

# Memória RAM para o histórico
chat_sessions = {}

# --- PROCESSO DE SONDAGEM RÍGIDO ---
PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor de expansão da Microlins. 
Seu objetivo é qualificar o lead seguindo este roteiro de 5 perguntas.
IMPORTANTE: Analise o histórico. Se a informação já foi dada, NÃO repita a pergunta.

ROTEIRO:
1º (ÁREA DE ATUAÇÃO) "Legal Sr, e me fala uma coisa, o Sr trabalha ou atua em qual área aí na sua cidade?"
2º (PRAÇA DE INTERESSE) "Ah legal, e me outra coisa, e o negócio pretende montar é aí na sua cidade mesmo?"
3º (PRAZO) "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio ou longo prazo? E o que seria médio ou longo prazo para o Sr?"
4º (LUCRO) "E me fala uma coisa Sr, esse negócio, pra ser bom para o Sr, ele precisa dar quanto na última linha?"
5º (CAPITAL DISPONÍVEL) "Legal Sr, para você ter uma ideia, a lucratividade está diretamente ao investimento. Qual valor você tem disponível para investir hoje?"

REGRAS:
- Uma pergunta por vez.
- Tom profissional, direto e humano.
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    # MODELO ATUALIZADO DE 2025
    MODELO = "gemini-3-flash-preview" # Ou "gemini-3-flash" se já estiver em GA

    if phone not in chat_sessions:
        chat_sessions[phone] = []

    try:
        # Registra a fala do lead
        chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})

        # Prepara o histórico estruturado para o Gemini 3
        contents = []
        for msg in chat_sessions[phone][-8:]: # Últimas 8 interações
            contents.append(types.Content(role=msg["role"], parts=[types.Part.from_text(text=msg["content"])]))

        # Chamada da API com Instrução de Sistema Nativa
        response = client.models.generate_content(
            model=MODELO,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=PROMPT_SISTEMA,
                temperature=0.7
            )
        )

        resposta_texto = response.text
        
        # Registra a resposta da IA no histórico
        chat_sessions[phone].append({"role": "model", "content": resposta_texto})
        
        return resposta_texto

    except Exception as e:
        print(f"❌ Erro na IA: {e}", flush=True)
        # Fallback simples caso a cota estoure
        return "Sr, tive uma pequena instabilidade no sistema. Poderia me confirmar em qual área o Sr atua hoje?"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200

    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"📩 Lead ({phone}): {msg}", flush=True)
        resp = gerar_resposta_ia(phone, msg)
        
        # Envio Z-API
        requests.post(
            f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
            json={"phone": phone, "message": resp}, 
            headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        )
        print(f"🤖 Bot: {resp}", flush=True)
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

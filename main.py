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

# Memória RAM para histórico
chat_sessions = {}

# PROCESSO DE SONDAGEM (As 5 perguntas solicitadas)
PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor de expansão. Seu objetivo é qualificar o lead seguindo este roteiro exato.
IMPORTANTE: Verifique o histórico para ver se a informação já foi dada. NÃO repita perguntas.

ROTEIRO DE QUALIFICAÇÃO:
1. (ÁREA DE ATUAÇÃO) "Legal Sr XXX, e me fala uma coisa, o Sr XXX trabalha ou atua em qual área aí na sua cidade?"
2. (PRAÇA DE INTERESSE) "Ah legal, e me outra coisa, e o negócio pretende montar é aí na sua cidade mesmo?"
3. (PRAZO) "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio ou longo prazo? E o que seria médio ou longo prazo para o Sr?"
4. (O QUANTO ESPERA LUCRAR) "E me fala uma coisa Sr XXX, esse negócio, pra ser bom para o Sr, ele precisa dar quanto na última linha?"
5. (CAPITAL DISPONÍVEL) "Legal Sr XXXX, para você ter uma ideia, a lucratividade está diretamente ao investimento. Tem um monte de franquia dizendo que com apenas 10 mil o Sr vai lucrar 50. E isso não é uma verdade. Qual valor você tem disponível para investir hoje?"

REGRAS:
- Se o lead respondeu a Cidade, pule para a Área de Atuação.
- Se ele já falou que é Pedreiro (Atuação), pergunte sobre a Praça.
- Use sempre o nome do Lead se ele tiver informado.
- Uma pergunta por vez.
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    # Modelo estável de Dez/2025
    MODELO = "gemini-2.0-flash"

    if phone not in chat_sessions:
        chat_sessions[phone] = []

    try:
        # Adiciona fala do lead ao histórico
        chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})

        # Prepara mensagens para a API
        contents = []
        for msg in chat_sessions[phone][-10:]: # Mantém contexto recente
            contents.append(types.Content(role=msg["role"], parts=[types.Part.from_text(text=msg["content"])]))

        # Chamada da API com Instrução de Sistema
        response = client.models.generate_content(
            model=MODELO,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=PROMPT_SISTEMA,
                temperature=0.7
            )
        )

        resposta_texto = response.text
        chat_sessions[phone].append({"role": "model", "content": resposta_texto})
        
        return resposta_texto

    except Exception as e:
        print(f"❌ Erro: {e}", flush=True)
        return "Sr, tive uma pequena instabilidade no sistema. Pode me confirmar sua última resposta?"

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
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

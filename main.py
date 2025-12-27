import os
import requests
import time
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

# Memória temporária (Histórico)
chat_sessions = {}

# SEU PROCESSO DE SONDAGEM RÍGIDO
PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor de expansão. Siga este roteiro RIGOROSAMENTE. 
Analise o histórico: se o lead já respondeu, pule para a próxima. 
NUNCA faça duas perguntas na mesma mensagem.

ROTEIRO:
1º (ÁREA DE ATUAÇÃO) "Legal Sr, e me fala uma coisa, o Sr trabalha ou atua em qual área aí na sua cidade?"
2º (PRAÇA DE INTERESSE) "Ah legal, e me outra coisa, e o negócio pretende montar é aí na sua cidade mesmo?"
3º (PRAZO) "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio ou longo prazo? E o que seria médio ou longo prazo para o Sr?"
4º (O QUANTO ESPERA LUCRAR) "E me fala uma coisa Sr, esse negócio, pra ser bom para o Sr, ele precisa dar quanto na última linha?"
5º (CAPITAL DISPONÍVEL) "Legal Sr, para você ter uma ideia, a lucratividade está diretamente ao investimento. Tem um monte de franquia dizendo que com apenas 10 mil o Sr vai lucrar 50. E isso não é uma verdade, pode inclusive consultar a própria base de franqueados. Qual valor você tem disponível para investir hoje?"
"""

@app.route("/", methods=["GET"])
def health(): return "Bot Ativo (Gemini 3.0 + Fallback 2.0)", 200

def gerar_resposta_ia(phone, mensagem_usuario):
    # Lista de prioridade: 3.0 Flash primeiro, 2.0 Flash como backup
    modelos_fallback = ["gemini-3.0-flash", "gemini-2.0-flash"]

    if phone not in chat_sessions:
        chat_sessions[phone] = []

    chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})
    
    # Prepara histórico (últimas 8 para equilíbrio de cota/contexto)
    contents = [
        types.Content(role=m["role"], parts=[types.Part.from_text(text=m["content"])]) 
        for m in chat_sessions[phone][-8:]
    ]

    for modelo in modelos_fallback:
        try:
            print(f"🔄 Tentando resposta com {modelo}...", flush=True)
            response = client.models.generate_content(
                model=modelo,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=PROMPT_SISTEMA,
                    temperature=0.3
                )
            )
            
            resposta_texto = response.text
            chat_sessions[phone].append({"role": "model", "content": resposta_texto})
            return resposta_texto

        except Exception as e:
            # Verifica se o erro é de limite de cota (429) ou sobrecarga
            error_msg = str(e).lower()
            if "429" in error_msg or "resource_exhausted" in error_msg:
                print(f"⚠️ Limite atingido no {modelo}. Mudando para o próximo...", flush=True)
                continue # Pula para o próximo modelo da lista
            else:
                print(f"❌ Erro crítico no {modelo}: {e}", flush=True)
                continue

    # Caso TODOS os modelos falhem (raro)
    return "Legal Sr! E me diga uma coisa, você trabalha em qual área aí na sua cidade hoje?"

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

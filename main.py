import os
import requests
import google.generativeai as genai
from flask import Flask, request

# --- SEUS DADOS DA Z-API (JÁ TESTADOS E FUNCIONANDO) ---
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"

# ⚠️ COLE SUA NOVA CHAVE AQUI DENTRO DAS ASPAS 👇
GEMINI_API_KEY = "AIzaSyDMCS--PV7v_9sVJbpACPv_5yGUyhdHlWY"

# Configuração da IA
genai.configure(api_key=GEMINI_API_KEY)
app = Flask(__name__)

# --- LÓGICA DE VENDAS (5 PERGUNTAS) ---
PROMPT_SISTEMA = """
Você é um consultor de expansão experiente. Siga esta ordem de sondagem rigorosa.
Analise o histórico. Se o lead já respondeu, vá para a próxima. Uma pergunta por vez.

1. (ÁREA) "Legal Sr(a), e me fala uma coisa, você trabalha ou atua em qual área hoje?"
2. (PRAÇA) "Ah legal, e o negócio que pretende montar é aí na sua cidade mesmo?"
3. (PRAZO) "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio/longo prazo?"
4. (LUCRO) "E me fala uma coisa, esse negócio, pra ser bom para você, precisa dar quanto de lucro mensal?"
5. (CAPITAL) "Legal. A lucratividade está ligada ao investimento. Qual valor você tem disponível hoje para esse projeto?"

Regra: Seja curto, profissional e leve. Não pule etapas.
"""

chat_sessions = {}

def gerar_resposta_ia(phone, mensagem_usuario):
    try:
        print(f"🧠 Consultando IA para {phone}...", flush=True)
        
        if phone not in chat_sessions:
            # Usando modelo 'gemini-pro' que é mais compatível e evita erro 404
            model = genai.GenerativeModel("gemini-pro")
            chat_sessions[phone] = model.start_chat(history=[])
        
        prompt = f"Instrução: {PROMPT_SISTEMA}\n\nLead disse: {mensagem_usuario}"
        response = chat_sessions[phone].send_message(prompt)
        return response.text
    except Exception as e:
        print(f"❌ ERRO IA: {e}", flush=True)
        # Fallback inteligente se a IA falhar
        return "Legal! E me conta, em qual área você atua hoje?"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe") is True: return "ok", 200

    mensagem = data.get("text", {}).get("message")
    phone = data.get("phone")

    if mensagem and phone:
        print(f"📩 RECEBIDO: {mensagem}", flush=True)
        
        # 1. Gera resposta com Inteligência
        resposta = gerar_resposta_ia(phone, mensagem)
        
        # 2. Envia via Z-API
        url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        headers = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        payload = {"phone": phone, "message": resposta}
        
        try:
            r = requests.post(url, json=payload, headers=headers)
            print(f"📤 ENVIO Z-API: {r.status_code}", flush=True)
        except Exception as e:
            print(f"❌ ERRO CONEXÃO: {e}", flush=True)
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)










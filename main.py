import os
import requests
import google.generativeai as genai
from flask import Flask, request

# --- CONFIGURAÇÕES ---
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"

# AGORA A MÁGICA: O código pega a chave escondida no Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
app = Flask(__name__)

# ... (Mantenha o resto do código igual, com o PROMPT_SISTEMA e a lógica)

genai.configure(api_key=GEMINI_API_KEY)
app = Flask(__name__)

PROMPT_SISTEMA = """
1. (ÁREA) "Legal Sr(a), e me fala uma coisa, você trabalha ou atua em qual área hoje?"
2. (PRAÇA) "Ah legal, e o negócio que pretende montar é aí na sua cidade mesmo?"
3. (PRAZO) "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio/longo prazo?"
4. (LUCRO) "E me fala uma coisa, esse negócio, pra ser bom para você, precisa dar quanto de lucro mensal?"
5. (CAPITAL) "Legal. A lucratividade está ligada ao investimento. Qual valor você tem disponível hoje para esse projeto?"
"""

chat_sessions = {}

def gerar_resposta_ia(phone, mensagem_usuario):
    try:
        # --- DIAGNÓSTICO DE MODELOS (Dedo-Duro) ---
        print("📋 LISTANDO MODELOS DISPONÍVEIS NA SUA CONTA:", flush=True)
        modelos_ok = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ DISPONÍVEL: {m.name}", flush=True)
                modelos_ok.append(m.name)
        
        # Tenta usar o modelo Flash, mas se não tiver, pega o primeiro da lista
        nome_modelo = "models/gemini-1.5-flash"
        if nome_modelo not in modelos_ok and modelos_ok:
            nome_modelo = modelos_ok[0] # Pega o primeiro que funcionar
            print(f"⚠️ Trocando para modelo disponível: {nome_modelo}", flush=True)

        if phone not in chat_sessions:
            print(f"🧠 Conectando no modelo: {nome_modelo}", flush=True)
            model = genai.GenerativeModel(nome_modelo)
            chat_sessions[phone] = model.start_chat(history=[])
        
        prompt = f"Contexto: {PROMPT_SISTEMA}\nLead: {mensagem_usuario}"
        response = chat_sessions[phone].send_message(prompt)
        return response.text

    except Exception as e:
        erro = f"🚨 ERRO FATAL IA: {str(e)}"
        print(erro, flush=True)
        return erro # Manda o erro pro WhatsApp para a gente ler

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe") is True: return "ok", 200

    mensagem = data.get("text", {}).get("message")
    phone = data.get("phone")

    if mensagem and phone:
        print(f"📩 RECEBIDO: {mensagem}", flush=True)
        resposta = gerar_resposta_ia(phone, mensagem)
        
        url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        headers = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        payload = {"phone": phone, "message": resposta}
        requests.post(url, json=payload, headers=headers)
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)










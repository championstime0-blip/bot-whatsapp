import os
import requests
import google.generativeai as genai
from flask import Flask, request

# --- CONFIGURAÇÕES ---
# Mantive seus dados aqui para facilitar, mas no Render podemos usar Variáveis de Ambiente
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"
GEMINI_API_KEY = "AIzaSyDuGUR_7z76h8njBGTD-LY8AOuN7Eb-Vlo"

genai.configure(api_key=GEMINI_API_KEY)
app = Flask(__name__)

# --- IA ---
PROMPT_SISTEMA = """Você é um consultor de expansão. Siga a ordem rigorosa:
1º (ÁREA DE ATUAÇÃO) Legal Sr XXX, em qual área você atua aí na sua cidade?
2º (PRAÇA) O negócio pretende montar é aí na sua cidade mesmo?
3º (PRAZO) Pretende abrir em 3 meses ou longo prazo? O que é longo prazo para você?
4º (LUCRO) Quanto esse negócio precisa dar na última linha para ser bom?
5º (CAPITAL) Explique que lucro exige investimento real (não apenas 10k). Pergunte quanto ele tem disponível hoje.
REGRAS: Uma pergunta por vez. Analise se o lead já respondeu."""

chat_sessions = {}

def gerar_resposta_ia(phone, mensagem_usuario):
    try:
        if phone not in chat_sessions:
            model = genai.GenerativeModel("gemini-1.5-flash")
            chat_sessions[phone] = model.start_chat(history=[])
        
        prompt = f"Instrução: {PROMPT_SISTEMA}\n\nLead disse: {mensagem_usuario}"
        response = chat_sessions[phone].send_message(prompt)
        return response.text
    except:
        return "Olá! Em qual área você atua hoje?"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe") is True: return "ok", 200

    mensagem = data.get("text", {}).get("message")
    phone = data.get("phone")

    if mensagem and phone:
        print(f"📩 Recebido: {mensagem}")
        resposta = gerar_resposta_ia(phone, mensagem)
        
        url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        headers = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        payload = {"phone": phone, "message": resposta}
        requests.post(url, json=payload, headers=headers)
            
    return "ok", 200
    import os
import requests
from flask import Flask, request

# --- SEUS DADOS DA Z-API ---
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    
    # Ignora mensagens enviadas por você mesmo
    if data.get("fromMe") is True:
        return "ok", 200

    mensagem = data.get("text", {}).get("message")
    phone = data.get("phone")

    if mensagem and phone:
        print(f"📩 RECEBIDO: {mensagem}", flush=True)
        
        # --- RESPOSTA SIMPLES (ECO) ---
        texto_resposta = f"🤖 Teste OK! Recebi: {mensagem}"
        
        # Envia de volta para a Z-API
        url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        headers = {
            "Client-Token": CLIENT_TOKEN,
            "Content-Type": "application/json"
        }
        payload = {
            "phone": phone,
            "message": texto_resposta
        }
        
        try:
            r = requests.post(url, json=payload, headers=headers)
            print(f"📤 STATUS Z-API: {r.status_code} | RETORNO: {r.text}", flush=True)
        except Exception as e:
            print(f"❌ ERRO DE CONEXÃO: {e}", flush=True)
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# Configuração necessária para o Render (Ele define a porta automaticamente)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)







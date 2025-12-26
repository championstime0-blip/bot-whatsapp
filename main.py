import os
import time
import requests
import google.generativeai as genai
from flask import Flask, request

# CONFIGURAÇÕES
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

app = Flask(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Memória volátil (RAM)
chat_sessions = {}

# PROMPT COM LÓGICA DE MEMÓRIA
PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor da Microlins.
SEU OBJETIVO: Coletar 4 informações (Cidade, Área atual, Prazo e Capital).

REGRAS DE MEMÓRIA:
1. Analise o histórico abaixo antes de perguntar.
2. Se o lead já respondeu uma pergunta, PASSE PARA A PRÓXIMA.
3. Não seja repetitivo. Se ele disse "Sou do Rio", não pergunte a cidade novamente.

ORDEM DAS PERGUNTAS:
1º Cidade? -> 2º Área de atuação? -> 3º Prazo (3 meses ou +)? -> 4º Capital disponível?
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    # Mudança para modelos com maior probabilidade de cota disponível
    modelos_candidatos = [
        "gemini-1.5-flash", # Modelo com maior cota gratuita (1500 req/dia)
        "gemini-pro",       # Modelo estável clássico
        "gemini-1.0-pro"    # Último recurso
    ]

    if phone not in chat_sessions:
        chat_sessions[phone] = []

    # Mantém apenas as últimas 10 mensagens para não gastar tokens
    historico_curto = chat_sessions[phone][-10:]

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando {nome_modelo}...", flush=True)
            model = genai.GenerativeModel(nome_modelo)
            
            # Formata o histórico para a IA entender o contexto
            contexto_com_historico = f"{PROMPT_SISTEMA}\n\nHistórico atual: {historico_curto}\n\nLead disse agora: {mensagem_usuario}"
            
            response = model.generate_content(contexto_com_historico)
            resposta_texto = response.text

            # Salva no histórico a troca de mensagens
            chat_sessions[phone].append(f"Lead: {mensagem_usuario}")
            chat_sessions[phone].append(f"Pedro: {resposta_texto}")
            
            return resposta_texto

        except Exception as e:
            print(f"❌ Erro no {nome_modelo}: {e}", flush=True)
            if "429" in str(e):
                continue # Tenta o próximo modelo
            continue

    return "Oi! Recebi sua mensagem, mas estou processando algumas informações aqui. Pode me dar 1 minutinho e já te respondo?"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200

    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"📩 Lead: {msg}", flush=True)
        resp = gerar_resposta_ia(phone, msg)
        
        requests.post(
            f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
            json={"phone": phone, "message": resp}, 
            headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        )
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

import os
import time
import requests
import google.generativeai as genai
from flask import Flask, request

# ==================================================
# 1. CONFIGURAÇÕES
# ==================================================
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"

# Pega a chave do ambiente
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

app = Flask(__name__)

# Configura o Google Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠️ ALERTA: GEMINI_API_KEY não encontrada no Environment!", flush=True)

# Memória RAM para guardar o histórico das conversas
chat_sessions = {}

# ==================================================
# 2. INTELIGÊNCIA ARTIFICIAL (CÉREBRO)
# ==================================================
PROMPT_SISTEMA = """
# ROLE: Consultor Pedro Lima (Expansão Ensina Mais Turma da Mônica).
# OBJETIVO: Qualificar lead para franquia.
# ROTEIRO:
1. PRACA: Cidade e Estado de interesse?
2. ATUACAO: Área de trabalho atual?
3. PRAZO: Interesse para agora (90 dias) ou futuro?
4. CAPITAL: Possui investimento disponível?

# REGRA:
- Seja curto e direto.
- Faça apenas uma pergunta por vez.
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    """
    Tenta usar os modelos disponíveis em 2025.
    Prioridade: 2.0 Flash (Estável) -> Latest (Genérico) -> 2.5 (Novo/Limitado)
    """
    modelos_candidatos = [
        "gemini-2.0-flash",       # <--- O CAMPEÃO (Apareceu no seu log)
        "gemini-flash-latest",    # <--- Genérico de segurança
        "gemini-2.5-flash"        # <--- Emergência (Cota baixa)
    ]

    # Inicializa sessão se não existir
    if phone not in chat_sessions:
        chat_sessions[phone] = {'history': []}

    prompt_completo = f"Instrução do Sistema: {PROMPT_SISTEMA}\n\nLead disse: {mensagem_usuario}"

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando modelo: {nome_modelo}...", flush=True)
            
            # Tenta carregar o modelo (tenta com e sem prefixo 'models/')
            try:
                model = genai.GenerativeModel(nome_modelo)
            except:
                model = genai.GenerativeModel(f"models/{nome_modelo}")

            # Inicia o chat com histórico
            chat = model.start_chat(history=chat_sessions[phone]['history'])
            response = chat.send_message(prompt_completo)
            
            # Se funcionou, salva o histórico e retorna
            chat_sessions[phone]['history'] = chat.history
            return response.text

        except Exception as e:
            erro_str = str(e)
            
            # Se for erro de Quota (429), espera e tenta o próximo
            if "429" in erro_str:
                print(f"⏳ Quota cheia no {nome_modelo}. Tentando outro...", flush=True)
                time.sleep(1) 
                continue 
            
            # Se for 404 (Não achou o modelo), apenas pula
            if "404" in erro_str or "not found" in erro_str.lower():
                print(f"⚠️ {nome_modelo} não encontrado. Pulando...", flush=True)
                continue
            
            # Outros erros
            print(f"❌ Erro genérico no {nome_modelo}: {erro_str}", flush=True)
            continue

    return "No momento nossos sistemas estão com alto volume. Tente novamente em 1 minuto."

# ==================================================
# 3. WEBHOOK (CONEXÃO WHATSAPP)
# ==================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe") is True: return "ok", 200

    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"📩 Lead: {msg}", flush=True)
        
        # Gera a resposta
        resp = gerar_resposta_ia(phone, msg)
        print(f"🤖 Bot: {resp}", flush=True)
        
        # Envia para o WhatsApp
        try:
            requests.post(
                f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
                json={"phone": phone, "message": resp}, 
                headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
            )
        except Exception as e:
            print(f"❌ Erro Z-API: {e}", flush=True)
            
    return "ok", 200

# Inicialização do Servidor
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

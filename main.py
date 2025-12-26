import os
import time
import requests
import google.generativeai as genai
from flask import Flask, request

# ==================================================
# 1. CONFIGURAÇÕES GERAIS
# ==================================================
# Seus dados da Z-API
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"

# Pega a chave do ambiente (Render) ou usa uma string vazia por segurança
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Inicializa Flask e Gemini
app = Flask(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠️ ALERTA: A variável GEMINI_API_KEY não foi detectada!")

# Memória Volátil (RAM) - Atenção: Reinicia se o servidor desligar
chat_sessions = {}

# ==================================================
# 2. INTELIGÊNCIA ARTIFICIAL (CÉREBRO)
# ==================================================
PROMPT_SISTEMA = """
# ROLE: Consultor Pedro Lima (Expansão Ensina Mais Turma da Mônica).
# MÉTODO: SPIN Selling. Objetivo: Agendar reunião de fechamento.
# PERSONA: Consultor humano, direto e profissional. NUNCA mencione que é uma IA.

# VARIÁVEIS DE QUALIFICAÇÃO (Roteiro de Sondagem):
Siga esta ordem rigorosa. Não pule etapas. Faça APENAS UMA pergunta por vez.

1. (PRACA): "Para verificar a disponibilidade na sua região: Em qual cidade você pensa em abrir a unidade?"
2. (ATUACAO): "Legal! E me fala uma coisa, você trabalha ou atua em qual área hoje?"
3. (PRAZO): "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio/longo prazo?"
4. (CAPITAL): "Legal. A lucratividade está ligada ao investimento. Qual valor você tem disponível hoje para esse projeto?"

# MATRIZ FINANCEIRA (Use apenas se perguntado):
- Modelo Center (>100k hab): R$ 147k total.
- Modelo Compacto (<100k hab): R$ 98k total.
- Lucro estimado: 40% líquido.

# REGRAS:
- Se o lead mostrar interesse imediato E tiver capital -> Convide para reunião.
- Seja breve. Respostas curtas funcionam melhor no WhatsApp.
"""

def gerar_resposta_ia(phone, mensagem_usuario):
    """
    Função resiliente: Tenta vários modelos até conseguir responder.
    """
    # Lista de Prioridade (Do mais rápido/barato para o mais compatível)
    modelos_candidatos = [
        "gemini-1.5-flash", 
        "gemini-1.5-pro", 
        "gemini-pro"
    ]

    # Cria ou recupera a sessão de chat
    if phone not in chat_sessions:
        # Se não tem sessão, cria uma "placeholder" para inicializar depois dentro do loop
        chat_sessions[phone] = {'history': []}

    prompt_completo = f"Instrução do Sistema: {PROMPT_SISTEMA}\n\nLead disse: {mensagem_usuario}"

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando modelo: {nome_modelo}...", flush=True)
            
            # Instancia o modelo da vez
            model = genai.GenerativeModel(nome_modelo)
            
            # Recria o chat com o histórico salvo na memória RAM
            chat = model.start_chat(history=chat_sessions[phone]['history'])
            
            # Tenta enviar a mensagem
            response = chat.send_message(prompt_completo)
            
            # Se deu certo, atualiza o histórico na memória
            chat_sessions[phone]['history'] = chat.history
            return response.text

        except Exception as e:
            erro_str = str(e)
            
            # Se for erro de Limite (Quota), espera um pouco
            if "429" in erro_str:
                print(f"⏳ Quota excedida no {nome_modelo}. Aguardando 2s...", flush=True)
                time.sleep(2) 
                continue # Tenta o próximo
            
            # Se for erro de Modelo não encontrado (404), apenas pula
            if "404" in erro_str or "not found" in erro_str.lower():
                print(f"⚠️ Modelo {nome_modelo} não encontrado. Pulando...", flush=True)
                continue
            
            # Outros erros
            print(f"❌ Erro no {nome_modelo}: {erro_str}", flush=True)
            continue

    # Se sair do loop, tudo falhou
    return "No momento estou com alta demanda de mensagens. Poderia me chamar novamente em 1 minuto?"

# ==================================================
# 3. CONEXÃO WHATSAPP (WEBHOOK)
# ==================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    
    # Ignora mensagens enviadas pelo próprio bot
    if data.get("fromMe") is True: 
        return "ok", 200

    mensagem = data.get("text", {}).get("message")
    phone = data.get("phone")

    if mensagem and phone:
        print(f"📩 Lead {phone}: {mensagem}", flush=True)
        
        # Gera resposta Inteligente
        resposta = gerar_resposta_ia(phone, mensagem)
        print(f"🤖 Bot respondeu: {resposta}", flush=True)
        
        # Envia para Z-API
        url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        headers = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        payload = {"phone": phone, "message": resposta}
        
        try:
            requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"❌ Erro ao enviar para Z-API: {e}", flush=True)
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

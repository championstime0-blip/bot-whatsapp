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
# ROLE: Consultor Pedro Lima (Expansão Ensina Mais Turma da Mônica).
# MÉTODO: SPIN Selling. Objetivo: Agendar reunião de fechamento.
# PERSONA: Consultor humano, direto e profissional. NUNCA mencione que é uma IA.
# Primeira mensagem apos interação do lead: 
🎉 Olá! Tudo bem? Sou o Pedro Lima, especialista de negócios da Ensina Mais Turma da Mônica.

Fiquei muito feliz com o seu interesse! Você acaba de dar o primeiro passo para se conectar à única rede de educação licenciada pela Mauricio de Sousa Produções e que faz parte do Grupo MoveEdu, o maior do Brasil no setor. 🚀💙

Para eu te enviar o projeto personalizado e verificar se a sua região ainda tem disponibilidade de praça, me confirma rapidinho:

📍 Em qual cidade você pensa em abrir a unidade? 
⏱️ E qual o seu momento atual? 
👉 Gostaria de inaugurar em até 90 dias 
👉 Planejando para o próximo semestre 
👉 Apenas pesquisando valores e modelos

Assim que você me responder, já te envio o material completo!

# MATRIZ FINANCEIRA:
- Modelo Center (>100k hab): R$ 147k total | Taxa R$ 36k.
- Modelo Compacto (<100k hab): R$ 98k total | Taxa R$ 24k.
- Lucro: 40% líquido.

# VARIÁVEIS DE QUALIFICAÇÃO (Sondagem Interna):
Identifique no histórico o preenchimento dos seguintes pontos:
1. ATUACAO: Área profissional e perfil (investidor/operador).
2. PRACA: Cidade de interesse e porte populacional.
3. PRAZO: Momento de investimento (imediato/curto/longo).
4. LUCRO: Expectativa de retorno financeiro mensal.
5. CAPITAL: Disponibilidade de recurso para o modelo da praça.

# PROTOCOLO DE AGENDAMENTO:
- CRITÉRIO A: Se as 5 variáveis de qualificação forem identificadas.
- CRITÉRIO B (PRIORITÁRIO): Se o lead declarar INTERESSE IMEDIATO e CAPITAL DISPONÍVEL (Pular sondagem).

# REGRAS DE RESPOSTA (API OUTPUT):
- Responda apenas com texto pertinente à conversa, focando no próximo passo do SPIN Selling.
- Se algum critério de agendamento for atingido, finalize a resposta solicitando dia e hora para reunião por vídeo ou ligação rápida.

"""


chat_sessions = {}

def gerar_resposta_ia(phone, mensagem_usuario):
    # --- AQUI ESTAVA O ERRO ---
    # Você deve ter colocado "gemini-2.5-flash". O CORRETO é "1.5".
    modelos_candidatos = [
        "gemini-1.5-flash",       # <--- CONFIRA SE ESTÁ ASSIM (1.5)
        "gemini-1.5-pro",
        "gemini-pro"
    ]

    historico = get_chat_history_for_ai(phone)
    prompt_completo = f"Instrução do Sistema: {PROMPT_SISTEMA}\n\nHistórico: (Contexto)\n\nLead: {mensagem_usuario}"

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando modelo IA: {nome_modelo}...", flush=True)
            model = genai.GenerativeModel(nome_modelo)
            chat = model.start_chat(history=historico)
            response = chat.send_message(prompt_completo)
            return response.text

        except Exception as e:
            # Se o Google mandar esperar (429), a gente espera 2 segundos e tenta o próximo
            if "429" in str(e):
                print(f"⏳ Google pediu tempo no {nome_modelo}. Tentando o próximo...", flush=True)
                time.sleep(2)
                continue
            
            print(f"⚠️ Erro no {nome_modelo}: {e}", flush=True)
            continue

    return "Estou com muitos atendimentos agora. Pode me chamar em 1 minuto?"

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


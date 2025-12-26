import os
import google.generativeai as genai
from flask import Flask, request, jsonify

# --- CONFIGURAÇÃO DO FLASK ---
app = Flask(__name__)

# --- CONFIGURAÇÃO DA IA (GEMINI) ---
# Certifique-se de configurar a variável GEMINI_API_KEY no painel do Render
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Modelo estável único para evitar erros 404
MODEL_NAME = "gemini-1.5-flash-latest"

# Configurações de comportamento da IA
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1000,
}

# --- PROMPT ESTRUTURADO (MICROLINS) ---
SYSTEM_INSTRUCTION = """
Você é o Consultor de Expansão da Microlins, rede do Grupo MoveEdu. Seu objetivo é qualificar leads para franquias 2026.
O modelo é o "Ecossistema 5 em 1" (Profissionalizantes, Inglês, Técnicos, Graduação e Pós).

DIRETRIZES DE SONDAGEM:
Analise o histórico e faça UMA pergunta por vez, seguindo esta ordem se ainda não respondidas:
1º (ÁREA DE ATUAÇÃO): "O Sr(a) trabalha ou atua em qual área profissional hoje?"
2º (PRAÇA DE INTERESSE): "Em qual cidade ou bairro você pretende montar o negócio?"
3º (PRAZO): "Pretende abrir nos próximos 3 meses ou é a médio/longo prazo? O que seria esse prazo para o Sr(a)?"
4º (LUCRO): "Para esse negócio ser bom, ele precisa dar quanto de lucro líquido (na última linha) por mês?"
5º (CAPITAL): "O investimento médio é de R$ 200 mil. Você possui esse capital disponível ou buscaria sócio/financiamento?"

REGRAS:
- Tom de voz: Profissional, empreendedor e objetivo.
- Se o lead não tiver capital nenhum, encerre educadamente.
- Se for da "Ensina Mais", avise que o chat está errado.
- Responda de forma curta para WhatsApp.
"""

model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config=generation_config,
    system_instruction=SYSTEM_INSTRUCTION
)

# --- ROTA DO WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    
    # Extração da mensagem do usuário (ajuste conforme seu provedor de WhatsApp)
    user_message = data.get('message') or data.get('text') or ""
    lead_name = data.get('name') or "Interessado"

    if not user_message:
        return jsonify({"status": "error", "message": "Mensagem vazia"}), 400

    try:
        # Inicia ou continua o chat com o contexto do lead
        chat_session = model.start_chat(history=[])
        
        # Envia a mensagem e recebe a resposta qualificada
        response = chat_session.send_message(user_message)
        bot_reply = response.text

        # Log para monitoramento no painel do Render
        print(f"📩 Lead ({lead_name}): {user_message}")
        print(f"🤖 Bot Microlins: {bot_reply}")

        return jsonify({
            "status": "success",
            "reply": bot_reply
        }), 200

    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERRO CRÍTICO: {error_msg}")
        
        # Tratamento de erro específico para quota/região
        if "429" in error_msg:
            reply = "Estamos com muitas solicitações. Tente em instantes."
        elif "403" in error_msg:
            reply = "Erro de permissão/região na API."
        else:
            reply = "Sistema em manutenção momentânea. Tente em 1 minuto."
            
        return jsonify({"status": "error", "reply": reply}), 500

# --- INICIALIZAÇÃO ---
if __name__ == '__main__':
    # O Render usa a porta 10000 por padrão via variável de ambiente PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

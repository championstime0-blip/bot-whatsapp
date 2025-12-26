import os
import google.generativeai as genai
from flask import Flask, request, jsonify

# --- 1. CONFIGURAÇÃO DO FLASK ---
app = Flask(__name__)

# --- 2. CONFIGURAÇÃO DA IA (GEMINI) ---
# Certifique-se de que a variável GEMINI_API_KEY esteja no painel do Render
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Modelo estável único para evitar erros 404 e 500
MODEL_NAME = "gemini-1.5-flash-latest"

# Configurações de comportamento da IA
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1000,
}

# --- 3. PROMPT ESTRUTURADO (MICROLINS) ---
SYSTEM_INSTRUCTION = """
Você é o Consultor de Expansão da Microlins. Seu objetivo é qualificar leads para franquias 2026.
O modelo é o "Ecossistema 5 em 1" (Profissionalizantes, Inglês, Técnicos, Graduação e Pós).

DIRETRIZES DE SONDAGEM:
Analise o histórico e faça UMA pergunta por vez, seguindo esta ordem se ainda não respondidas:
1º (ÁREA DE ATUAÇÃO): "O Sr(a) trabalha ou atua em qual área profissional hoje?"
2º (PRAÇA DE INTERESSE): "Em qual cidade ou bairro você pretende montar o negócio?"
3º (PRAZO): "Pretende abrir nos próximos 3 meses ou é a médio/longo prazo?"
4º (LUCRO): "Para esse negócio ser bom, quanto de lucro líquido mensal você espera?"
5º (CAPITAL): "O investimento é de R$ 200 mil. Você possui esse capital ou buscaria sócio/financiamento?"

REGRAS:
- Tom de voz: Profissional e direto.
- Se o lead não tiver capital, encerre educadamente.
- Se for da "Ensina Mais", avise que o chat está errado.
"""

# Inicialização do modelo com instrução de sistema
model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config=generation_config,
    system_instruction=SYSTEM_INSTRUCTION
)

# --- 4. ROTA DO WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def webhook():
    # Recebe os dados brutos do request
    data = request.get_json()
    
    # CORREÇÃO DO ERRO DE DICIONÁRIO:
    # Extraímos apenas o valor da chave 'message' como STRING
    user_message = ""
    if data and 'message' in data:
        user_message = str(data['message'])
    elif data and 'text' in data:
        user_message = str(data['text'])

    # Se não houver texto, retornamos erro 400
    if not user_message or user_message.strip() == "":
        return jsonify({"status": "error", "message": "Mensagem vazia"}), 400

    try:
        # Inicia a sessão de chat
        chat_session = model.start_chat(history=[])
        
        # Envia apenas a STRING para a API
        response = chat_session.send_message(user_message)
        bot_reply = response.text

        # Logs para você acompanhar no painel do Render
        print(f"📩 Mensagem recebida: {user_message}")
        print(f"🤖 Resposta do Bot: {bot_reply}")

        return jsonify({
            "status": "success",
            "reply": bot_reply
        }), 200

    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERRO NA CHAMADA API: {error_msg}")
        return jsonify({"status": "error", "reply": "Sistema em manutenção momentânea."}), 500

# --- 5. INICIALIZAÇÃO PARA O RENDER ---
if __name__ == '__main__':
    # O Render exige o uso da variável de ambiente PORT (padrão 10000)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

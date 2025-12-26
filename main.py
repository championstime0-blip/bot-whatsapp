import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Nome técnico estável para evitar conflito de versão da API
MODEL_NAME = "models/gemini-1.5-flash"

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1000,
}

SYSTEM_INSTRUCTION = """
Você é o Consultor de Expansão da Microlins. Qualifique leads 2026 (Ecossistema 5 em 1).
Pergunte na ordem: 1. Área de atuação | 2. Praça | 3. Prazo | 4. Lucro esperado | 5. Capital (R$ 200k).
Seja direto e profissional.
"""

model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config=generation_config,
    system_instruction=SYSTEM_INSTRUCTION
)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    # Extração segura da string de mensagem
    user_message = ""
    if data:
        user_message = str(data.get('message', data.get('text', '')))

    if not user_message.strip():
        return jsonify({"status": "error", "message": "Mensagem vazia"}), 400

    try:
        # Gera o conteúdo diretamente usando a instrução de sistema
        response = model.generate_content(user_message)
        bot_reply = response.text

        return jsonify({
            "status": "success",
            "reply": bot_reply
        }), 200

    except Exception as e:
        print(f"❌ ERRO NA CHAMADA API: {str(e)}")
        return jsonify({"status": "error", "reply": "Instabilidade momentânea. Tente em 1 min."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

import os
import requests
from flask import Flask, request
from groq import Groq

# --- CONFIGURAÇÕES ---
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY)

# Memória RAM para histórico
chat_sessions = {}

# SEU PROCESSO DE SONDAGEM RÍGIDO
PROMPT_SISTEMA = """
Você é o Pedro Lima, consultor de expansão da Microlins. 
Seu objetivo é qualificar o lead com estas 5 perguntas exatas. 
NUNCA repita perguntas já respondidas. Analise o histórico antes de falar.

ROTEIRO OBRIGATÓRIO:
1º (ÁREA DE ATUAÇÃO) "Legal Sr, e me fala uma coisa, o Sr trabalha ou atua em qual área aí na sua cidade?"
2º (PRAÇA DE INTERESSE) "Ah legal, e me outra coisa, e o negócio pretende montar é aí na sua cidade mesmo?"
3º (PRAZO) "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio ou longo prazo? E o que seria médio ou longo prazo para o Sr?"
4º (LUCRO) "E me fala uma coisa Sr, esse negócio, pra ser bom para o Sr, ele precisa dar quanto na última linha?"
5º (CAPITAL DISPONÍVEL) "Legal Sr, para você ter uma ideia, a lucratividade está diretamente ao investimento. Tem um monte de franquia dizendo que com apenas 10 mil o Sr vai lucrar 50. E isso não é uma verdade. Qual valor você tem disponível para investir hoje?"

REGRAS: 
- Use tom profissional e direto. 
- Apenas UMA pergunta por vez.
"""

@app.route("/", methods=["GET"])
def health(): return "Llama 3.1 Ativo", 200

def gerar_resposta_ia(phone, mensagem_usuario):
    if phone not in chat_sessions:
        chat_sessions[phone] = [{"role": "system", "content": PROMPT_SISTEMA}]

    # Adiciona fala do lead
    chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})

    try:
        # Chamada para o Llama 3.1 8B na Groq
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=chat_sessions[phone][-8:], # Envia as últimas 8 mensagens
            temperature=0.5,
            max_tokens=1024,
        )
        
        resposta = completion.choices[0].message.content
        chat_sessions[phone].append({"role": "assistant", "content": resposta})
        return resposta

    except Exception as e:
        print(f"Erro Llama: {e}", flush=True)
        return "Legal! E me diga uma coisa, você trabalha em qual área aí na sua cidade hoje?"

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
        print(f"🤖 Pedro Lima: {resp}", flush=True)
            
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

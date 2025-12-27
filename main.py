import os
import requests
from flask import Flask, request
from groq import Groq

# --- SUAS CREDENCIAIS ---
Z_API_ID = "3EC502952818632B0E31C6B75FFFD411"
Z_API_TOKEN = "43FB843CF98C6CD27D3E0E50"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S" 

# Configurações do Render
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

chat_sessions = {}

# --- CÉREBRO TREINADO COM O PDF MICROLINS 2025 ---
PROMPT_SISTEMA = """
Você é Pedro Lima, Especialista de Negócios da Microlins (Grupo MoveEdu).
OBJETIVO: Apresentar a franquia, tirar dúvidas com base no Book 2025 e qualificar o lead para uma reunião.

### BASE DE CONHECIMENTO (Book 2025):
- **O Negócio (5 em 1):** Ecossistema completo: 1. Profissionalizante, 2. Inglês, 3. Técnico, 4. Graduação, 5. Pós-Graduação.
- **Autoridade:** +30 anos, 4 milhões de alunos, +400 unidades. Selo de Excelência ABF.
- **Números Reais:**
  - Investimento: A partir de R$ 120 mil (cidades > 50k hab).
  - Faturamento: Escolas maduras > R$ 100 mil/mês.
  - Lucratividade: 25% a 35%. Payback 18-24 meses.

### ROTEIRO DE QUALIFICAÇÃO (Siga a ordem):
1. **NOME:** "Olá! Sou o Pedro Lima da Microlins. Com quem eu falo?"
2. **CIDADE:** "Prazer! O Sr(a) fala de qual cidade? Pretende montar a escola aí mesmo?"
3. **CAPITAL (Filtro):** "Para alinhar o modelo ideal (temos formatos a partir de 120k), qual capital o Sr(a) dispõe para investimento inicial hoje?"
4. **LUCRO:** "E para esse negócio fazer sentido para você, quanto você espera que ele deixe de lucro líquido mensal?"
5. **PRAZO:** "Entendi. E sua ideia é iniciar esse projeto de imediato (próximos 3 meses) ou é algo mais para médio prazo?"

### REGRA DE ENCERRAMENTO:
- **Lead Qualificado (Capital > 100k):** Convide para call com o Diretor.
- **Lead Desqualificado:** Explique sobre o investimento necessário e encerre educadamente.
"""

@app.route("/", methods=["GET"])
def health(): return "Microlins Bot (Llama 3.3) Ativo", 200

def gerar_resposta_ia(phone, mensagem_usuario):
    if not client: return "Erro: Chave Groq não configurada."
    
    if phone not in chat_sessions:
        chat_sessions[phone] = [{"role": "system", "content": PROMPT_SISTEMA}]
    
    chat_sessions[phone].append({"role": "user", "content": mensagem_usuario})

    try:
        # ATUALIZADO: Usando o modelo Llama 3.3 (Mais novo e suportado)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_sessions[phone][-10:],
            temperature=0.3,
        )
        resposta = completion.choices[0].message.content
        chat_sessions[phone].append({"role": "assistant", "content": resposta})
        return resposta
    except Exception as e:
        print(f"Erro IA: {e}")
        # Fallback de segurança para o modelo menor se o 70b falhar
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=chat_sessions[phone][-10:],
                temperature=0.3,
            )
            resposta = completion.choices[0].message.content
            chat_sessions[phone].append({"role": "assistant", "content": resposta})
            return resposta
        except:
            return "Olá! Pode repetir por favor?"

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
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

import os
import requests
from flask import Flask, request
from groq import Groq

# --- DADOS DA SUA IMAGEM ---
Z_API_ID = "3EC502952818632B0E31C6B75FFFD411"
Z_API_TOKEN = "43FB843CF98C6CD27D3E0E50"
CLIENT_TOKEN = "F12d5b62bed3f447598b17c727045141cS" 
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
chat_sessions = {}

# Roteiro solicitado
PROMPT_SISTEMA = """Você é Pedro Lima, Especialista de negocios da Microlins (Grupo MoveEdu).
Seu objetivo é apresentar a franquia, tirar dúvidas e QUALIFICAR o lead para uma reunião.

### BASE DE CONHECIMENTO (Use para responder dúvidas):
- **A Marca:** Maior rede de ensino profissionalizante do Brasil. 30+ anos, 4 milhões de alunos.
- **O Grande Diferencial:** Modelo "Ecossistema 5 em 1". Uma única escola oferece: 1. Profissionalizante, 2. Inglês, 3. Técnico, 4. Graduação, 5. Pós-Graduação. Faturamento maximizado.
- **Investimento:** A partir de R$ 150 mil (Cidades > 50k hab). Existem linhas de crédito (BB, Santander).
- **Retorno:** Lucratividade de 25% a 35%. Payback estimado de 18 a 24 meses.
- **Suporte:** Escolha do ponto, treinamento (Iron Manager), marketing e gestão.

### SEU ROTEIRO DE QUALIFICAÇÃO (Siga esta ordem):
1. **NOME:** (Se não souber) "Olá! Sou o Pedro Lima da Microlins. Com quem eu falo?"
2. **CIDADE:** "Prazer! O Sr(a) fala de qual cidade? Pretende montar a escola aí mesmo?"
3. **CAPITAL (O Filtro):** "Para alinhar o modelo ideal (temos formatos a partir de 150k), qual capital o Sr(a) dispõe para investimento inicial hoje?"
4. **LUCRO:** "E para esse negócio fazer sentido para você, quanto você espera que ele deixe de lucro líquido mensal?"
5. **PRAZO:** "Entendi. E sua ideia é iniciar esse projeto de imediato (próximos 3 meses) ou é algo mais para médio prazo?"

### REGRAS DE DECISÃO (O Grande Final):
- **LEAD QUALIFICADO (Tem Capital > 100k + Interesse):**
  Finalize dizendo: "Excelente perfil, [Nome]. Gostaria de agendar uma call com nosso Diretor para apresentar os números da sua cidade. Qual o melhor horário para você?"

- **LEAD DESQUALIFICADO (Capital muito baixo ou procura emprego):**
  Finalize educadamente: "Entendo, [Nome]. Como nosso modelo de franquia exige um investimento inicial mínimo e capital de giro, talvez este não seja o momento ideal. Posso manter seu contato para futuras oportunidades com modelos menores?"

### DIRETRIZES DE COMPORTAMENTO:
- Se o lead perguntar algo, responda com a Base de Conhecimento e IMEDIATAMENTE faça a próxima pergunta do roteiro.
- Seja empático, mas firme nos números. Não prometa milagres.
"""

@app.route("/", methods=["GET"])
def health(): return "OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200
    
    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        # 1. Gerar resposta com Llama 3.1
        if phone not in chat_sessions:
            chat_sessions[phone] = [{"role": "system", "content": PROMPT_SISTEMA}]
        chat_sessions[phone].append({"role": "user", "content": msg})
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=chat_sessions[phone][-6:],
            temperature=0.3
        )
        resp = completion.choices[0].message.content

        # 2. Enviar para Z-API com DEBUG
        zapi_url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        payload = {"phone": phone, "message": resp}
        headers = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        
        try:
            r = requests.post(zapi_url, json=payload, headers=headers, timeout=10)
            print(f"DEBUG Z-API: Status {r.status_code} - Resposta: {r.text}", flush=True)
        except Exception as e:
            print(f"ERRO CONEXAO Z-API: {e}", flush=True)
            
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)



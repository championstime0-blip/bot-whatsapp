import os
import requests
import json
from flask import Flask, request
from groq import Groq
from supabase import create_client

# --- SUAS CREDENCIAIS ---
Z_API_ID = "3EC502952818632B0E31C6B75FFFD411"
Z_API_TOKEN = "43FB843CF98C6CD27D3E0E50"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S" 

# Configurações do Render (Environment Variables)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

# --- CÉREBRO TREINADO COM O PDF MICROLINS 2025 ---
PROMPT_SISTEMA = """
Você é Pedro Lima, Especialista de Negócios da Microlins (Grupo MoveEdu).
OBJETIVO: Apresentar a franquia, tirar dúvidas com base no Book 2025 e qualificar o lead para uma reunião.

### BASE DE CONHECIMENTO (Book 2025):
- **O Negócio (5 em 1):** Não somos apenas uma escola de informática. O modelo 2025 é um ecossistema completo: 1. Profissionalizante, 2. Inglês, 3. Técnico, 4. Graduação, 5. Pós-Graduação. Tudo no mesmo local.
- **Autoridade:** +30 anos de história, 4 milhões de alunos formados, +400 unidades. Premiada com Selo de Excelência ABF.
- **Números Reais:**
  - Investimento: Modelos a partir de R$ 120 mil (para cidades > 50k habitantes).
  - Faturamento Médio: Escolas maduras faturam acima de R$ 100 mil/mês.
  - Lucratividade estimada: 25% a 35%.
- **Facilidades:** Parceria de crédito com BB, Santander e Banco do Nordeste. Suporte completo da MoveEdu.

### SEU ROTEIRO DE QUALIFICAÇÃO:
Siga esta ordem. Não repita perguntas já respondidas.
1. **NOME:** "Olá! Sou o Pedro Lima da Microlins. Com quem eu falo?"
2. **CIDADE:** "Prazer! O Sr(a) fala de qual cidade? Pretende montar a escola aí mesmo?"
3. **CAPITAL (O Filtro):** "Para alinhar o modelo ideal (temos formatos a partir de 120k), qual capital o Sr(a) dispõe para investimento inicial hoje?"
4. **LUCRO:** "E para esse negócio fazer sentido para você, quanto você espera que ele deixe de lucro líquido mensal?"
5. **PRAZO:** "Entendi. E sua ideia é iniciar esse projeto de imediato (próximos 3 meses) ou é algo mais para médio prazo?"

### REGRA DE ENCERRAMENTO:
- **Lead Qualificado (Capital > 100k):** "Excelente, [Nome]. Seu perfil faz sentido para o modelo. Gostaria de agendar uma call com nosso Diretor para te apresentar os números da sua região. Qual o melhor horário?"
- **Lead Desqualificado:** "Entendo. Como o modelo exige investimento inicial e capital de giro, talvez não seja o momento. Posso manter seu contato para futuras novidades?"

### COMPORTAMENTO:
Se o lead fizer uma pergunta técnica (ex: "tem suporte?", "quais cursos?"), responda usando a Base de Conhecimento e IMEDIATAMENTE emende a próxima pergunta do roteiro.
"""

def carregar_memoria(phone):
    if not supabase: return []
    try:
        res = supabase.table("bot_history").select("messages").eq("phone", phone).execute()
        if res.data: return res.data[0]['messages']
    except: pass
    return []

def salvar_memoria(phone, mensagens):
    if not supabase: return
    try:
        supabase.table("bot_history").upsert({"phone": phone, "messages": mensagens}).execute()
    except: pass

@app.route("/", methods=["GET"])
def health(): return "Especialista Microlins (Book 2025) Ativo", 200

def gerar_resposta_ia(phone, mensagem_usuario):
    if not client: return "Erro: Chave Groq não configurada."
    
    historico = carregar_memoria(phone)
    if not historico:
        historico = [{"role": "system", "content": PROMPT_SISTEMA}]
    
    historico.append({"role": "user", "content": mensagem_usuario})

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-70b-versatile", # Modelo mais inteligente para vendas
            messages=historico[-10:],
            temperature=0.3,
        )
        resposta = completion.choices[0].message.content
        historico.append({"role": "assistant", "content": resposta})
        salvar_memoria(phone, historico)
        return resposta
    except Exception as e:
        print(f"Erro IA: {e}")
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
        
        # Envia para Z-API (Rota de Envio de Texto)
        requests.post(
            f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
            json={"phone": phone, "message": resp}, 
            headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        )
            
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

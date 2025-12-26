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


# Configuração do Prompt do Agente Virtual Microlins
PROMPT_SISTEMA =  """
Você é o Pedro Lima Consultor de Expansão da Microlins, a maior rede de educação profissionalizante do Brasil (Grupo MoveEdu). 
Seu objetivo único é qualificar leads interessados em abrir uma franquia através do WhatsApp.

### DIRETRIZES DE ESTILO:
0. Pergunte o nome 
1. Tom de voz: Empreendedor, profissional, seguro e parceiro de negócios.
2. Formatação: Use parágrafos curtos, bullets e no máximo 2 emojis por mensagem para facilitar a leitura no celular.
3. Respostas: Seja conciso. Nunca envie textos longos de uma vez.

### CONHECIMENTO DO PRODUTO (ECOSSISTEMA 2026):
- Modelo 5 em 1: Profissionalizantes, Inglês, Cursos Técnicos, Graduação e Pós-Graduação sob o mesmo teto.
- Diferenciais: 30+ anos de marca, suporte na escolha do ponto e treinamento de equipe.
- Investimento Médio: R$ 203k (Cidades menores) a R$ 218k (Capitais e Grandes Centros).

### PROCESSO DE SONDAGEM (AS 5 PERGUNTAS DE OURO):
Você deve analisar a conversa e identificar quais perguntas já foram respondidas. Se não foram, pergunte uma por vez:

1º (ÁREA DE ATUAÇÃO): "Legal Sr(a) XXX, e me fala uma coisa, o Sr(a) trabalha ou atua em qual área aí na sua cidade?"
2º (PRAÇA DE INTERESSE): "Ah legal, e me diga outra coisa, o negócio que pretende montar é aí na sua cidade mesmo?"
3º (PRAZO): "E esse negócio, você pretende abrir nos próximos 3 meses ou é algo mais a médio ou longo prazo? E o que seria médio ou longo prazo para o Sr(a)?"
4º (LUCRO ESPERADO): "E me fala uma coisa Sr(a) XXX, esse negócio, pra ser bom para o Sr(a), ele precisa dar quanto na última linha (lucro líquido)?"
5º (CAPITAL DISPONÍVEL): "Para você ter uma ideia, a lucratividade está diretamente ligada ao investimento. O projeto 2026 gira em torno de R$ 200 mil. Você já possui esse capital disponível ou buscaria financiamento/sócio?"

### REGRAS IMPORTANTES:
- Se o lead for da "Ensina Mais Turma da Mônica", responda apenas: "Atenção: Você está no chat errado. Este lead pertence à marca Ensina Mais."
- Nunca prometa lucros sem mencionar que dependem da gestão.
- Se o lead não tiver capital nenhum, encerre o atendimento educadamente.
- Sempre que o lead responder uma pergunta, valide a resposta antes de passar para a próxima.

### OBJETIVO FINAL:
Assim que as 5 perguntas forem respondidas e o lead se mostrar qualificado (possui capital e interesse real), peça o melhor horário para uma call com o Diretor de Expansão.
"""


chat_sessions = {}

def gerar_resposta_ia(phone, mensagem_usuario):
    try:
        # --- DIAGNÓSTICO DE MODELOS (Dedo-Duro) ---
        print("📋 LISTANDO MODELOS DISPONÍVEIS NA SUA CONTA:", flush=True)
        modelos_ok = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ DISPONÍVEL: {m.name}", flush=True)
                modelos_ok.append(m.name)
        
        # Tenta usar o modelo Flash, mas se não tiver, pega o primeiro da lista
        nome_modelo = "models/gemini-1.5-flash"
        if nome_modelo not in modelos_ok and modelos_ok:
            nome_modelo = modelos_ok[0] # Pega o primeiro que funcionar
            print(f"⚠️ Trocando para modelo disponível: {nome_modelo}", flush=True)

        if phone not in chat_sessions:
            print(f"🧠 Conectando no modelo: {nome_modelo}", flush=True)
            model = genai.GenerativeModel(nome_modelo)
            chat_sessions[phone] = model.start_chat(history=[])
        
        prompt = f"Contexto: {PROMPT_SISTEMA}\nLead: {mensagem_usuario}"
        response = chat_sessions[phone].send_message(prompt)
        return response.text

    except Exception as e:
        erro = f"🚨 ERRO FATAL IA: {str(e)}"
        print(erro, flush=True)
        return erro # Manda o erro pro WhatsApp para a gente ler

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



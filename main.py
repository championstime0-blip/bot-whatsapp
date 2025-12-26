import os
import time
import requests
import google.generativeai as genai
from flask import Flask, request

# CONFIGURAÇÕES
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

app = Flask(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

chat_sessions = {}

PROMPT_SISTEMA = """
Você é o Pedro Lima Consultor de Expansão da Microlins, a maior rede de educação profissionalizante do Brasil (Grupo MoveEdu). 
Seu objetivo único é qualificar leads interessados em abrir uma franquia através do WhatsApp.

### DIRETRIZES DE ESTILO:
0. Pergunte nome, nunca nome completo 
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

def gerar_resposta_ia(phone, mensagem_usuario):
    # Usamos o modelo Lite que é mais estável para conversas longas
    nome_modelo = "models/gemini-2.0-flash-lite"

    # 1. Recupera ou cria o histórico na memória do servidor
    if phone not in chat_sessions:
        chat_sessions[phone] = [] # Lista vazia para novos leads

    try:
        model = genai.GenerativeModel(nome_modelo)
        
        # 2. Iniciamos o chat passando o HISTÓRICO REAL que salvamos
        chat = model.start_chat(history=chat_sessions[phone])
        
        # 3. O Prompt agora é uma "Instrução de Verificação"
        instrucao_contexto = f"""
        INSTRUÇÕES:
        - Você é o Pedro Lima da Microlins.
        - CONSULTE o histórico de mensagens acima antes de responder.
        - Se o lead JÁ RESPONDEU uma pergunta (ex: Cidade, Área de atuação), NÃO REPITA a pergunta.
        - Avance para a próxima pergunta do roteiro de sondagem.
        
        ROTEIRO: 1.Cidade? -> 2.Área? -> 3.Prazo? -> 4.Capital?
        
        RESPOSTA ANTERIOR DO LEAD: {mensagem_usuario}
        """

        response = chat.send_message(instrucao_contexto)
        
        # 4. SALVAMOS O HISTÓRICO ATUALIZADO (Isso é o que evita a repetição)
        # O 'chat.history' contém a conversa completa atualizada
        chat_sessions[phone] = chat.history
        
        return response.text

    except Exception as e:
        print(f"Erro na IA: {e}")
        return "Tive um pequeno problema técnico, mas já estou voltando. Pode repetir sua última resposta?"
    # ESTRATÉGIA 2025: Usar a versão LITE para ter mais cota gratuita
    modelos_candidatos = [
        "models/gemini-2.0-flash-lite", # <--- MAIOR COTA EM 2025
        "models/gemini-2.0-flash-exp",
        "models/gemini-flash-lite-latest"
    ]

    if phone not in chat_sessions:
        chat_sessions[phone] = {'history': []}
    
    # Limita o histórico para as últimas 6 mensagens (evita erro de memória/tokens)
    if len(chat_sessions[phone]['history']) > 6:
        chat_sessions[phone]['history'] = chat_sessions[phone]['history'][-6:]

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando modelo estável: {nome_modelo}...", flush=True)
            model = genai.GenerativeModel(nome_modelo)
            chat = model.start_chat(history=chat_sessions[phone]['history'])
            
            response = chat.send_message(f"{PROMPT_SISTEMA}\nLead: {mensagem_usuario}")
            
            chat_sessions[phone]['history'] = chat.history
            return response.text

        except Exception as e:
            erro = str(e)
            print(f"❌ Falha no {nome_modelo}: {erro}", flush=True)
            if "429" in erro or "limit" in erro.lower():
                time.sleep(2) # Espera o cooldown do Google
                continue
            continue

    return "Oi! Recebi sua mensagem. Pode me dar um minutinho? Meu sistema de viabilidade está processando os dados de Salvador/região."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe") is True: return "ok", 200

    msg = data.get("text", {}).get("message")
    phone = data.get("phone")

    if msg and phone:
        print(f"📩 Lead ({phone}): {msg}", flush=True)
        resp = gerar_resposta_ia(phone, msg)
        
        requests.post(
            f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text",
            json={"phone": phone, "message": resp}, 
            headers={"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        )
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)



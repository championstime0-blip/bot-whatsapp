import os
import json
import time
import requests
import datetime
import google.generativeai as genai
from flask import Flask, request, render_template_string, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

# ==================================================
# 1. CONFIGURAÇÕES
# ==================================================

# DADOS Z-API (Seus dados fixos)
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"

# SEGURANÇA GOOGLE (Pega do "Cofre" do Render)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ACESSO AO DASHBOARD
ADMIN_USER = "pedro"
ADMIN_PASS = "mudar123"  # Recomendado: Mude para uma senha forte depois

# APP E BANCO DE DADOS
app = Flask(__name__)
app.secret_key = "chave_secreta_para_sessao_flask" 

# Configuração Automática do Banco (SQLite local ou Postgres no Render)
database_url = os.environ.get("DATABASE_URL", "sqlite:///leads.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configuração Inicial da IA
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠️ ALERTA: Chave GEMINI_API_KEY não encontrada nas Variáveis de Ambiente!")

# ==================================================
# 2. BANCO DE DADOS (MODELOS)
# ==================================================
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), default="Lead WhatsApp")
    status = db.Column(db.String(50), default="Novo") 
    history = db.Column(db.Text, default="[]") 
    last_interaction = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Cria as tabelas na primeira execução
with app.app_context():
    db.create_all()

# ==================================================
# 3. CÉREBRO DA IA (PROMPT & LÓGICA BLINDADA)
# ==================================================

PROMPT_SISTEMA = """
# ROLE: Consultor Pedro Lima (Expansão Ensina Mais Turma da Mônica).
# MÉTODO: SPIN Selling. Objetivo: Agendar reunião de fechamento.
# PERSONA: Humano, profissional, leve. Nunca diga que é IA.

# PRIMEIRO CONTATO:
Se o histórico estiver vazio, apresente-se:
"🎉 Olá! Tudo bem? Sou o Pedro Lima, especialista de negócios da Ensina Mais Turma da Mônica. Fiquei muito feliz com o seu interesse! Para eu verificar a disponibilidade na sua região, me conta: Em qual cidade você pensa em abrir a unidade?"

# ROTEIRO DE SONDAGEM (Siga a ordem se o lead ainda não respondeu):
1. PRACA: Cidade e Estado de interesse?
2. ATUACAO: Qual sua área de atuação hoje?
3. PRAZO: Pretende abrir em até 90 dias ou médio/longo prazo?
4. CAPITAL: Possui capital disponível para investimento imediato?

# REGRAS:
- Uma pergunta por vez.
- Se o lead responder tudo e tiver capital + urgência -> Convide para reunião.
- Responda dúvidas curtas sobre a franquia (Lucro 40%, Investimento a partir de 98k).
"""

def get_chat_history_for_ai(phone):
    """Recupera as últimas mensagens do banco para dar memória à IA"""
    lead = Lead.query.filter_by(phone=phone).first()
    history_ai = []
    if lead:
        try:
            raw_history = json.loads(lead.history)
            # Pega as últimas 15 mensagens para não estourar o limite
            for msg in raw_history[-15:]:
                role = "user" if msg['role'] == "user" else "model"
                history_ai.append({"role": role, "parts": [msg['text']]})
        except:
            history_ai = []
    return history_ai

def gerar_resposta_ia(phone, mensagem_usuario):
    """
    FUNÇÃO BLINDADA: Tenta vários modelos se um falhar (404 ou 429).
    """
    modelos_candidatos = [
        "gemini-1.5-flash",       # 1º: Rápido e Barato
        "gemini-1.5-pro",         # 2º: Mais inteligente
        "gemini-1.0-pro",         # 3º: Estável
        "gemini-pro"              # 4º: Legado
    ]

    historico = get_chat_history_for_ai(phone)
    # Adiciona a mensagem atual ao prompt se o histórico estiver vazio no objeto chat,
    # mas aqui enviamos via prompt para garantir contexto do sistema.
    prompt_completo = f"Instrução do Sistema: {PROMPT_SISTEMA}\n\nHistórico Recente: (Ver Contexto)\n\nLead disse agora: {mensagem_usuario}"

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando modelo IA: {nome_modelo}...", flush=True)
            
            model = genai.GenerativeModel(nome_modelo)
            chat = model.start_chat(history=historico)
            
            response = chat.send_message(prompt_completo)
            return response.text

        except Exception as e:
            erro_str = str(e)
            if "404" in erro_str or "not found" in erro_str.lower():
                print(f"⚠️ Modelo {nome_modelo} não existe (404). Pulando...", flush=True)
                continue
            
            elif "429" in erro_str or "quota" in erro_str.lower():
                print(f"⏳ Quota excedida no {nome_modelo} (429). Aguardando 1s...", flush=True)
                time.sleep(1) 
                continue
            
            else:
                print(f"❌ Erro genérico no {nome_modelo}: {erro_str}", flush=True)
                continue

    print("🚨 ERRO CRÍTICO: Nenhum modelo respondeu.", flush=True)
    return "No momento nossos sistemas estão com alto volume. Poderia me chamar novamente em 1 minuto?"

# ==================================================
# 4. FUNÇÕES AUXILIARES E ROTAS
# ==================================================

def save_message(phone, role, text):
    """Salva mensagens no banco de dados"""
    with app.app_context():
        lead = Lead.query.filter_by(phone=phone).first()
        if not lead:
            lead = Lead(phone=phone)
            db.session.add(lead)
        
        try:
            history_list = json.loads(lead.history)
        except:
            history_list = []
            
        history_list.append({
            "role": role, 
            "text": text, 
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        lead.history = json.dumps(history_list)
        lead.last_interaction = datetime.datetime.utcnow()
        lead.status = "Em Conversa"
        db.session.commit()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTA DE LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return "<h3>Senha incorreta! <a href='/login'>Tentar de novo</a></h3>"
    
    return """
    <div style='text-align:center; margin-top:50px; font-family:sans-serif;'>
        <h2>🔐 Acesso Restrito - Pedro Lima Bot</h2>
        <form method="post">
            <input type="text" name="username" placeholder="Usuário" required style="padding:10px;"><br><br>
            <input type="password" name="password" placeholder="Senha" required style="padding:10px;"><br><br>
            <button type="submit" style="padding:10px 20px; cursor:pointer;">Entrar</button>
        </form>
    </div>
    """

# --- ROTA DASHBOARD (LISTA) ---
@app.route('/dashboard')
@login_required
def dashboard():
    leads = Lead.query.order_by(Lead.last_interaction.desc()).all()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard Leads</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <meta http-equiv="refresh" content="30">
    </head>
    <body class="container mt-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>🎯 Gestão de Leads - MoveEdu</h2>
            <span class="badge bg-success">Online</span>
        </div>
        <div class="card shadow">
            <div class="card-body">
                <table class="table table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Telefone</th>
                            <th>Status</th>
                            <th>Última Interação</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for lead in leads %}
                        <tr>
                            <td>{{ lead.phone }}</td>
                            <td><span class="badge bg-primary">{{ lead.status }}</span></td>
                            <td>{{ lead.last_interaction.strftime('%d/%m %H:%M') }}</td>
                            <td>
                                <a href="/dashboard/{{ lead.phone }}" class="btn btn-sm btn-info">Ver Chat</a>
                                <a href="https://wa.me/{{ lead.phone }}" target="_blank" class="btn btn-sm btn-outline-success">WhatsApp Web</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, leads=leads)

# --- ROTA DASHBOARD (DETALHE) ---
@app.route('/dashboard/<phone>')
@login_required
def view_lead(phone):
    lead = Lead.query.filter_by(phone=phone).first_or_404()
    try:
        history = json.loads(lead.history)
    except:
        history = []
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chat: {{ lead.phone }}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container mt-4">
            <a href="/dashboard" class="btn btn-secondary mb-3">← Voltar</a>
            <div class="card shadow">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">Conversa com {{ lead.phone }}</h5>
                </div>
                <div class="card-body" style="height: 600px; overflow-y: auto; background: #e5ddd5;">
                    {% for msg in history %}
                        <div class="d-flex {{ 'justify-content-start' if msg.role == 'model' else 'justify-content-end' }} mb-3">
                            <div class="card" style="max-width: 75%; {{ 'background: white;' if msg.role == 'model' else 'background: #dcf8c6;' }}">
                                <div class="card-body p-2">
                                    <small class="text-muted fw-bold">{{ '🤖 Pedro Lima' if msg.role == 'model' else '👤 Lead' }}</small>
                                    <p class="mb-1">{{ msg.text }}</p>
                                    <small class="text-muted" style="font-size: 0.7em;">{{ msg.time }}</small>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, lead=lead, history=history)

# --- ROTA WEBHOOK (Z-API) ---
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    
    # 1. Ignora mensagens enviadas pelo próprio bot (Loop infinito)
    if data.get("fromMe") is True: 
        return "ok", 200

    mensagem = data.get("text", {}).get("message")
    phone = data.get("phone")

    # 2. Processa apenas se tiver mensagem e telefone
    if mensagem and phone:
        print(f"📩 RECEBIDO DE {phone}: {mensagem}", flush=True)
        
        # A. Salva o que o Lead disse
        save_message(phone, "user", mensagem)
        
        # B. Gera resposta (Com tentativa em vários modelos)
        resposta = gerar_resposta_ia(phone, mensagem)
        print(f"🧠 IA RESPONDEU: {resposta}", flush=True)
        
        # C. Salva o que a IA disse
        save_message(phone, "model", resposta)
        
        # D. Envia para o WhatsApp via Z-API
        url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        headers = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        payload = {"phone": phone, "message": resposta}
        
        try:
            requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"❌ ERRO Z-API: {e}", flush=True)
            
    return "ok", 200

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)






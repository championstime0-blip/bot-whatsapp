import os
import json
import time
import requests
import datetime
import google.generativeai as genai
from flask import Flask, request, render_template_string, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

# ==================================================
# 1. CONFIGURAÇÕES
# ==================================================
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"

# Pega a chave do ambiente (Render)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

ADMIN_USER = "pedro"
ADMIN_PASS = "mudar123"

app = Flask(__name__)
app.secret_key = "segredo_absoluto_moveedu"

# Banco de Dados
database_url = os.environ.get("DATABASE_URL", "sqlite:///leads.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ==================================================
# 2. MODELO DE DADOS
# ==================================================
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), default="Lead")
    status = db.Column(db.String(50), default="Novo") 
    history = db.Column(db.Text, default="[]") 
    last_interaction = db.Column(db.DateTime, default=datetime.datetime.utcnow)

with app.app_context():
    db.create_all()

# ==================================================
# 3. CÉREBRO (LÓGICA BLINDADA)
# ==================================================
PROMPT_SISTEMA = """
# ROLE: Consultor Pedro Lima (Expansão Ensina Mais Turma da Mônica).
# OBJETIVO: Qualificar lead para franquia.
# ROTEIRO DE SONDAGEM:
1. PRACA: Cidade e Estado de interesse?
2. ATUACAO: Qual sua área de atuação hoje?
3. PRAZO: Pretende abrir em até 90 dias ou médio/longo prazo?
4. CAPITAL: Possui capital disponível para investimento?
# REGRA: Uma pergunta por vez. Seja curto e profissional.
"""

# --- A FUNÇÃO QUE FALTAVA FOI REINSERIDA AQUI 👇 ---
def get_chat_history_for_ai(phone):
    """Recupera histórico do banco para contexto da IA"""
    lead = Lead.query.filter_by(phone=phone).first()
    history_ai = []
    if lead:
        try:
            raw_history = json.loads(lead.history)
            # Pega as últimas 10 trocas para não estourar limite
            for msg in raw_history[-10:]:
                role = "user" if msg['role'] == "user" else "model"
                history_ai.append({"role": role, "parts": [msg['text']]})
        except:
            history_ai = []
    return history_ai

def gerar_resposta_ia(phone, mensagem_usuario):
    # Lista CORRETA de modelos (Removido o 2.5 que não existe)
    modelos_candidatos = [
        "gemini-1.5-flash", 
        "gemini-1.5-pro", 
        "gemini-pro"
    ]

    # Chama a função que agora existe!
    historico = get_chat_history_for_ai(phone)
    prompt_completo = f"Instrução: {PROMPT_SISTEMA}\n\nHistórico: (Contexto)\n\nLead disse: {mensagem_usuario}"

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando modelo IA: {nome_modelo}...", flush=True)
            
            model = genai.GenerativeModel(nome_modelo)
            chat = model.start_chat(history=historico)
            
            response = chat.send_message(prompt_completo)
            return response.text

        except Exception as e:
            erro_str = str(e)
            if "429" in erro_str:
                print(f"⏳ Quota excedida no {nome_modelo}. Aguardando 2s...", flush=True)
                time.sleep(2) # Espera o castigo do Google passar
                continue
            
            print(f"⚠️ Erro no {nome_modelo}: {erro_str}", flush=True)
            continue

    return "Nossos sistemas estão sobrecarregados. Tente novamente em 1 minuto."

# ==================================================
# 4. ROTAS E WEBHOOK
# ==================================================
def save_message(phone, role, text):
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

# Rota de Login Simplificada
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect('/dashboard')
    return "<form method='post'><input name='username' placeholder='user'><br><input type='password' name='password' placeholder='pass'><br><button>Login</button></form>"

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session: return redirect('/login')
    leads = Lead.query.order_by(Lead.last_interaction.desc()).all()
    # Tabela simples
    rows = ""
    for l in leads:
        rows += f"<tr><td>{l.phone}</td><td>{l.status}</td><td><a href='https://wa.me/{l.phone}'>Abrir Whats</a></td></tr>"
    return f"<table border='1' cellpadding='10'><thead><tr><th>Telefone</th><th>Status</th><th>Ação</th></tr></thead><tbody>{rows}</tbody></table>"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe") is True: return "ok", 200

    mensagem = data.get("text", {}).get("message")
    phone = data.get("phone")

    if mensagem and phone:
        print(f"📩 RECEBIDO: {mensagem}", flush=True)
        save_message(phone, "user", mensagem)
        
        resposta = gerar_resposta_ia(phone, mensagem)
        print(f"🤖 IA: {resposta}", flush=True)
        save_message(phone, "model", resposta)
        
        url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        headers = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}
        payload = {"phone": phone, "message": resposta}
        
        try:
            requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"❌ ERRO Z-API: {e}", flush=True)
            
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

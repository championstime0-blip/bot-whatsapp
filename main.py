import os
import json
import time
import requests
import datetime
import google.generativeai as genai
from flask import Flask, request, render_template_string, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import google.generativeai as genai
# ... outros imports ...

# --- DIAGNÓSTICO DE VERSÃO ---
try:
    import importlib.metadata
    v = importlib.metadata.version("google-generativeai")
    print(f"🛑 VERSÃO DO GOOGLE INSTALADA: {v}", flush=True)
except:
    print("🛑 NÃO FOI POSSÍVEL LER A VERSÃO", flush=True)
# -----------------------------
# ==================================================
# 1. CONFIGURAÇÕES
# ==================================================
Z_API_ID = "3EC3280430DD02449072061BA788E473"
Z_API_TOKEN = "34E8E958D060C21D55F5A3D8"
CLIENT_TOKEN = "Ff1119996b44848dbaf394270f9933163S"

# Pega a chave do Render. Se não tiver, tenta pegar do ambiente local (fallback)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

ADMIN_USER = "pedro"
ADMIN_PASS = "mudar123"

app = Flask(__name__)
app.secret_key = "segredo_absoluto"

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
# 3. CÉREBRO (LÓGICA BLINDADA V2)
# ==================================================
PROMPT_SISTEMA = """
# ROLE: Consultor Pedro Lima (Expansão Ensina Mais Turma da Mônica).
# OBJETIVO: Qualificar lead para franquia.
# ROTEIRO:
1. PRACA: Cidade e Estado?
2. ATUACAO: Área de trabalho atual?
3. PRAZO: Interesse para agora (90 dias) ou futuro?
4. CAPITAL: Possui investimento disponível?
# REGRA: Uma pergunta por vez. Seja curto.
"""

def get_historico(phone):
    lead = Lead.query.filter_by(phone=phone).first()
    history_ai = []
    if lead:
        try:
            raw = json.loads(lead.history)
            for msg in raw[-10:]: # Pega últimas 10
                role = "user" if msg['role'] == "user" else "model"
                history_ai.append({"role": role, "parts": [msg['text']]})
        except: pass
    return history_ai

def gerar_resposta_ia(phone, mensagem):
    # Lista de tentativas (Do melhor para o mais compatível)
    modelos = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    historico = get_historico(phone)
    prompt = f"Instrução: {PROMPT_SISTEMA}\nLead: {mensagem}"

    for modelo in modelos:
        try:
            print(f"🔄 Tentando {modelo}...", flush=True)
            model = genai.GenerativeModel(modelo)
            chat = model.start_chat(history=historico)
            response = chat.send_message(prompt)
            return response.text
        except Exception as e:
            erro = str(e)
            if "404" in erro or "not found" in erro.lower():
                print(f"⚠️ {modelo} 404 (Não achou). Pulando...", flush=True)
                continue
            if "429" in erro:
                print(f"⏳ {modelo} 429 (Quota). Pulando...", flush=True)
                time.sleep(1)
                continue
            print(f"❌ Erro no {modelo}: {erro}", flush=True)
            continue
            
    return "Nossos consultores estão todos ocupados. Tente em 1 minuto."

# ==================================================
# 4. ROTAS E WEBHOOK
# ==================================================
def save_msg(phone, role, text):
    with app.app_context():
        lead = Lead.query.filter_by(phone=phone).first()
        if not lead:
            lead = Lead(phone=phone)
            db.session.add(lead)
        try: hist = json.loads(lead.history)
        except: hist = []
        hist.append({"role": role, "text": text, "time": str(datetime.datetime.now())})
        lead.history = json.dumps(hist)
        lead.last_interaction = datetime.datetime.utcnow()
        db.session.commit()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("fromMe"): return "ok", 200
    
    msg = data.get("text", {}).get("message")
    phone = data.get("phone")
    
    if msg and phone:
        print(f"📩 Lead {phone}: {msg}", flush=True)
        save_msg(phone, "user", msg)
        
        resp = gerar_resposta_ia(phone, msg)
        print(f"🤖 Bot: {resp}", flush=True)
        save_msg(phone, "model", resp)
        
        url = f"https://api.z-api.io/instances/{Z_API_ID}/token/{Z_API_TOKEN}/send-text"
        requests.post(url, json={"phone": phone, "message": resp}, headers={
            "Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"
        })
    return "ok", 200

# ROTA DE LOGIN SIMPLIFICADA
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect('/dashboard')
    return "<form method='post'><input name='username'><input type='password' name='password'><button>Login</button></form>"

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session: return redirect('/login')
    leads = Lead.query.order_by(Lead.last_interaction.desc()).all()
    rows = "".join([f"<tr><td>{l.phone}</td><td>{l.status}</td><td><a href='https://wa.me/{l.phone}'>Whats</a></td></tr>" for l in leads])
    return f"<table border='1'>{rows}</table>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)








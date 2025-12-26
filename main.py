def gerar_resposta_ia(phone, mensagem_usuario):
    """
    Estratégia 2025:
    1. Tenta o 2.0 Flash (Versão Estável com muita cota).
    2. Tenta o 'latest' (Apelido genérico que o Google sempre mantém ativo).
    3. Deixa o 2.5 pro final (Pois tem cota baixa de 20 msgs).
    """
    modelos_candidatos = [
        "gemini-2.0-flash",       # <--- O CAMPEÃO (Estável em Dez/25)
        "gemini-flash-latest",    # <--- O GENÉRICO (Sempre funciona)
        "gemini-2.5-flash"        # <--- O NOVO (Cota Baixa - Só emergência)
    ]

    # Inicializa sessão se não existir
    if phone not in chat_sessions:
        chat_sessions[phone] = {'history': []}

    prompt_completo = f"Instrução: {PROMPT_SISTEMA}\n\nLead disse: {mensagem_usuario}"

    for nome_modelo in modelos_candidatos:
        try:
            print(f"🔄 Tentando modelo: {nome_modelo}...", flush=True)
            
            # ATENÇÃO: Alguns modelos precisam do prefixo 'models/'
            if "models/" not in nome_modelo:
                nome_modelo_full = f"models/{nome_modelo}"
            else:
                nome_modelo_full = nome_modelo

            # Tenta instanciar (com e sem o prefixo 'models/' se der erro)
            try:
                model = genai.GenerativeModel(nome_modelo)
            except:
                model = genai.GenerativeModel(nome_modelo_full)

            chat = model.start_chat(history=chat_sessions[phone]['history'])
            response = chat.send_message(prompt_completo)
            
            # Se deu certo, salva e retorna
            chat_sessions[phone]['history'] = chat.history
            return response.text

        except Exception as e:
            erro_str = str(e)
            
            # Se for cota (429), espera um pouco
            if "429" in erro_str:
                print(f"⏳ Quota cheia no {nome_modelo}. Tentando outro...", flush=True)
                time.sleep(1) 
                continue 
            
            # Se for 404 (Não achou), pula
            if "404" in erro_str or "not found" in erro_str.lower():
                print(f"⚠️ {nome_modelo} não disponível. Pulando...", flush=True)
                continue
            
            print(f"❌ Erro {nome_modelo}: {erro_str}", flush=True)
            continue

    return "No momento nossos sistemas estão com alto volume. Tente em 1 minuto."

import streamlit as st
import streamlit_authenticator as stauth
import bcrypt
import pyperclip
from openai import OpenAI
import pandas as pd
import sqlite3
from key_management import gerar_chave_unica, armazenar_chave_usuario, enviar_chave_por_email

# Configuração inicial do banco de dados
def criar_tabela_usuarios():
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                (username TEXT PRIMARY KEY, name TEXT, senha TEXT, chave TEXT, is_admin INTEGER)''')
    conn.commit()
    conn.close()

criar_tabela_usuarios()

# Função para adicionar usuários com privilégio de administrador
def adicionar_usuario(username, name, senha, chave, is_admin=0):
    hashed_password = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute("INSERT INTO usuarios (username, name, senha, chave, is_admin) VALUES (?, ?, ?, ?, ?)",
              (username, name, hashed_password, chave, is_admin))
    conn.commit()
    conn.close()

# Função para verificar a chave e cadastrar o usuário
def verificar_chave_e_cadastrar(username, name, senha, chave_fornecida):
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE chave=?", (chave_fornecida,))
    if c.fetchone() is None:  # Chave é única e válida
        adicionar_usuario(username, name, senha, chave_fornecida)
        st.success("Cadastro realizado com sucesso!")
    else:
        st.error("Chave inválida ou já utilizada.")
    conn.close()

# Função para acessar o banco de dados e obter usuários
def obter_usuarios():
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute("SELECT username, name, is_admin FROM usuarios")
    usuarios = c.fetchall()
    conn.close()
    return usuarios

# Função para definir um usuário como administrador
def definir_administrador(username, status):
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute("UPDATE usuarios SET is_admin = ? WHERE username = ?", (status, username))
    conn.commit()
    conn.close()
    st.success(f"Usuário {username} atualizado com sucesso!")

# Interface no Streamlit para gerenciar administradores
def gerenciar_administradores():
    st.title("Gerenciar Administradores")
    usuarios = obter_usuarios()
    
    for usuario in usuarios:
        username, name, is_admin = usuario
        status = st.checkbox(f"{name} ({username})", value=bool(is_admin))
        if st.button(f"Atualizar {username}"):
            definir_administrador(username, int(status))

# Página de Cadastro de Usuário
def pagina_cadastro():
    st.title("Cadastro de Usuário")
    nome_completo = st.text_input("Nome Completo")
    nome_usuario = st.text_input("Nome de Usuário")
    senha = st.text_input("Senha", type="password")
    chave_fornecida = st.text_input("Chave Única de Cadastro")
    if st.button("Cadastrar"):
        if nome_completo and nome_usuario and senha and chave_fornecida:
            verificar_chave_e_cadastrar(nome_usuario, nome_completo, senha, chave_fornecida)
        else:
            st.error("Por favor, preencha todos os campos.")

# Página de geração e envio de chaves (apenas para administradores)
def pagina_admin():
    if st.session_state.is_admin:
        st.title("Gerar e Enviar Chaves")
        username = st.text_input("Nome de Usuário para Gerar a Chave")
        email_destino = st.text_input("Email do Destinatário")
        
        if st.button("Gerar e Enviar Chave"):
            if username and email_destino:
                chave = gerar_chave_unica()
                armazenar_chave_usuario(username, chave)
                enviar_chave_por_email(email_destino, chave)
                st.success(f"Chave gerada e enviada para {email_destino}")
            else:
                st.error("Por favor, preencha todos os campos.")
    else:
        st.error("Você não tem permissão para acessar esta página.")

# Página de Login e Verificação de Usuário
def pagina_login():
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute("SELECT username, name, senha, is_admin FROM usuarios")
    usuarios = c.fetchall()
    conn.close()

    usernames = [usuario[0] for usuario in usuarios]
    names = [usuario[1] for usuario in usuarios]
    hashed_passwords = [usuario[2] for usuario in usuarios]
    is_admin_list = {usuario[0]: usuario[3] for usuario in usuarios}  # Mapear is_admin

    authenticator = stauth.Authenticate(names, usernames, hashed_passwords, "cookie_name", "random_key", cookie_expiry_days=30)
    name, authentication_status, username = authenticator.login("Login", "main")

    if authentication_status:
        st.session_state.is_admin = bool(is_admin_list[username])  # Salvar status de admin na sessão
        st.write(f"Bem-vindo, {name}!")
        if st.session_state.is_admin:
            pagina_admin()       # Chama a função de administração se o usuário for administrador
        client = OpenAI(api_key=st.secrets["api_keys"]["openai"]) # Configure sua chave de API da OpenAI

        if 'documentos_pendentes' not in st.session_state:
            st.session_state.documentos_pendentes = []
        if 'aprova_doc' not in st.session_state:
            st.session_state.aprova_doc = None 

        # Função para gerar documento jurídico
        def gerar_documento_juridico(prompt,chat):
            st.warning("Gerando peça...")
            response = client.chat.completions.create(
                model=chat,  # Certifique-se de usar o modelo correto
                messages=[
                    {"role": "system", "content": "Você é um assistente jurídico especializado em criar documentos legais."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()

        # Função para criar a tabela no banco de dados
        def criar_tabela():
            conn = sqlite3.connect('documentos.db')
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS documentos
                        (id INTEGER PRIMARY KEY, cliente TEXT, servico TEXT, data TEXT, detalhes TEXT, documento TEXT)''')
            conn.commit()
            conn.close()

        # Função para salvar documento no banco de dados
        def salvar_documento(cliente, servico, data, detalhes, documento):
            conn = sqlite3.connect('documentos.db')
            c = conn.cursor()
            c.execute("INSERT INTO documentos (cliente, servico, data, detalhes, documento) VALUES (?, ?, ?, ?, ?)",
                    (cliente, servico, data, detalhes, documento))
            conn.commit()
            conn.close()

        # Função para excluir documento do banco de dados
        def excluir_documento(doc_id):
            conn = sqlite3.connect('documentos.db')
            c = conn.cursor()
            c.execute("DELETE FROM documentos WHERE id = ?", (doc_id,))
            conn.commit()
            conn.close()

        # Função para carregar documentos do banco de dados
        def carregar_documentos():
            conn = sqlite3.connect('documentos.db')
            c = conn.cursor()
            c.execute("SELECT * FROM documentos")
            documentos = c.fetchall()
            conn.close()
            return documentos

        # Função para verificar se o documento está completo e profissional
        def verificar_documento(documento,chat):
            # Verificação de referências a leis
            leis_mencionadas = ["art.", "lei nº", "parágrafo"]
            contem_leis = any(lei in documento.lower() for lei in leis_mencionadas)
            # Verificação de coerência no contexto jurídico
            prompt_verificacao = f"Verifique a seguinte peça jurídica para garantir que ela faz sentido no contexto jurídico e contém referências adequadas às leis{contem_leis}:\n\n{documento}\n\nResponda 'Aprovada, sem novas observações' se a peça é adequada, ou 'Não' se não for. Caso a resposta seja 'Não', justifique e sugira quais pontos ou leis devem ser revisadas."
            response = client.chat.completions.create(
                model=chat,
                messages=[
                    {"role": "system", "content": "Você é um assistente jurídico especializado em revisar documentos legais."},
                    {"role": "user", "content": prompt_verificacao}
                ]
            )
            validacao = response.choices[0].message.content
            return validacao
            
        # Configuração do Streamlit
        st.title("Gerador de Documentos Jurídicos com IA")

        # Chamar a função para criar a tabela no banco de dados
        criar_tabela()

        # Entrada de dados
        st.header("Dados dos Clientes")
        num_clientes = st.number_input("Número de Clientes", min_value=1, step=1)

        clientes_data = []
        for i in range(num_clientes):
            cliente = st.text_input(f"Cliente {i+1} Nome", key=f"cliente_nome_{i}")
            servico = st.text_input(f"Cliente {i+1} Serviço", key=f"cliente_servico_{i}")
            data = st.date_input(f"Cliente {i+1} Data", key=f"cliente_data_{i}")
            detalhes = st.text_area(f"Cliente {i+1} Detalhes do Caso", key=f"cliente_detalhes_{i}")
            clientes_data.append({'Cliente': cliente, 'Serviço': servico, 'Data': data, 'Detalhes': detalhes})
        chat = st.selectbox(
            "Qual modelo a ser utilizado?",
            ("gpt-4o", "gpt-4o-mini"),
        )  
        df = pd.DataFrame(clientes_data)

        # Geração dos documentos
        if st.button("Gerar Documentos"):
            if not df.empty:
                for index, row in df.iterrows():
                    prompt = f"Crie um {row['Serviço']} para {row['Cliente']} com data {row['Data']}.\nDetalhes do caso: {row['Detalhes']}. Pesquise na internet por processos similares e leis para ter suporte jurídico."
                    documento = gerar_documento_juridico(prompt,chat)
                    aprovacao = verificar_documento(documento,chat)
                    st.warning("Finalizou")
                    st.session_state.documentos_pendentes.append({
                        'cliente': row['Cliente'],
                        'servico': row['Serviço'],
                        'data': str(row['Data']),
                        'detalhes': row['Detalhes'],
                        'documento': documento,
                        'validacao': aprovacao,
                        'prompt': prompt
                    })
            else:
                st.warning("Por favor, insira os dados dos clientes.")

        # Função para gerar novo prompt com base nas observações do assistente revisor
        def gerar_novo_prompt(original_prompt, observacoes):
            novo_prompt = f"{original_prompt}\nPor favor, leve em consideração as seguintes observações ao refazer a peça:\n{observacoes}"
            return novo_prompt

        # Aprovação dos documentos pendentes
        if st.session_state.documentos_pendentes:
            st.header("Documentos Pendentes de Aprovação")
            for i, doc in enumerate(st.session_state.documentos_pendentes):
                st.subheader(f"Documento para {doc['cliente']}:")
                st.text_area(f"{doc['servico']} para {doc['cliente']}", doc['documento'], height=300, key=f"doc_text_{i}")
                st.write("Observações do revisor:")
                st.write(doc['validacao'])
                
                if st.session_state.aprova_doc is None:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("Aprovar", key=f"aprovar_{i}"):
                            st.session_state.aprova_doc = True
                    with col2:
                        if st.button("Rejeitar", key=f"rejeitar_{i}"):
                            st.session_state.aprova_doc = False
                    with col3:
                        if st.button("Refazer com as Observações sugeridas", key=f"refazer_{i}"):
                            novo_prompt = gerar_novo_prompt(doc['prompt'], doc['validacao'])
                            novo_documento = gerar_documento_juridico(novo_prompt, chat)
                            nova_validacao = verificar_documento(novo_documento, chat)
                            st.session_state.documentos_pendentes[i]['documento'] = novo_documento
                            st.session_state.documentos_pendentes[i]['validacao'] = nova_validacao
                            st.session_state.documentos_pendentes[i]['prompt'] = novo_prompt
                            st.experimental_rerun()

                if st.session_state.aprova_doc is not None:
                    if st.session_state.aprova_doc:
                        salvar_documento(doc['cliente'], doc['servico'], doc['data'], doc['detalhes'], doc['documento'])
                        st.success(f"Documento para {doc['cliente']} salvo com sucesso!")
                    else:
                        st.error(f"O documento gerado para {doc['cliente']} não atende aos critérios de qualidade. Motivo: {doc['validacao']}")
                    
                    st.session_state.documentos_pendentes.pop(i)
                    st.session_state.aprova_doc = None
                    st.rerun()

        # Função para copiar texto para a área de transferência
        def copiar_para_area_transferencia(texto):
            pyperclip.copy(texto)
            st.success("Texto copiado para a área de transferência!")
        # Exibir documentos salvos
        st.header("Documentos Salvos")
        documentos_salvos = carregar_documentos()
        for doc in documentos_salvos:
            st.subheader(f"Documento para {doc[1]}:")
            texto_documento = doc[5]
            st.text_area(f"{doc[2]} para {doc[1]}", texto_documento, height=300)
            # Botão para copiar o conteúdo do documento para a área de transferência
            if st.button(f"Copiar Documento {doc[0]} para a Área de Transferência", key=f"copiar_{doc[0]}"):
                copiar_para_area_transferencia(texto_documento)
            if st.button(f"Excluir Documento {doc[0]}", key=f"excluir_{doc[0]}"):
                excluir_documento(doc[0])
                st.success(f"Documento {doc[0]} excluído com sucesso!")
                st.rerun()
        authenticator.logout("Logout", "sidebar")
    elif authentication_status == False:
        st.error("Usuário ou senha incorretos")
    elif authentication_status == None:
        st.warning("Por favor, insira seu usuário e senha.")

# Seleção de Página
st.sidebar.title("Navegação")
if st.session_state.is_admin:
    pagina = st.sidebar.radio("Ir para", ["Login", "Cadastro de Usuário", "Administração"])
else:
    pagina = st.sidebar.radio("Ir para", ["Login", "Cadastro de Usuário"])

if pagina == "Cadastro de Usuário":
    pagina_cadastro()
elif pagina == "Administração" and st.session_state.is_admin:
    pagina_admin()
else:
    pagina_login()

import secrets
import sqlite3
import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Função para gerar uma chave única
def gerar_chave_unica():
    return secrets.token_hex(16)

# Função para armazenar a chave no banco de dados associada a um usuário autorizado
def armazenar_chave_usuario(username, chave):
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute("UPDATE usuarios SET chave=? WHERE username=?", (chave, username))
    conn.commit()
    conn.close()

# Função para enviar a chave por e-mail
def enviar_chave_por_email(email_destino, chave, username):
    remetente = st.secrets["email"]["remetente"]
    senha = st.secrets["email"]["senha"]
    
    # Configurar servidor SMTP para Yahoo com SSL
    with smtplib.SMTP_SSL("smtp.mail.yahoo.com", 465) as servidor:
        servidor.login(remetente, senha)
        
        mensagem = MIMEMultipart()
        mensagem["From"] = remetente
        mensagem["To"] = email_destino
        mensagem["Subject"] = "Sua Chave de Cadastro"
        
        corpo_email = f"Sua chave de cadastro é: {chave}\nE seu usuário é: {username}"
        mensagem.attach(MIMEText(corpo_email, "plain"))
        
        servidor.send_message(mensagem)
        print("E-mail enviado com sucesso!")

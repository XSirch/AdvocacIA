import secrets
import sqlite3
import smtplib
from email.mime.text import MIMEText

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
def enviar_chave_por_email(email_destino, chave):
    remetente = "christianoccruz@yahoo.com.br"
    senha = "sua_senha"

    mensagem = MIMEText(f"Sua chave de cadastro única é: {chave}")
    mensagem["Subject"] = "Chave de Cadastro"
    mensagem["From"] = remetente
    mensagem["To"] = email_destino

    with smtplib.SMTP_SSL("smtp.example.com", 465) as servidor:
        servidor.login(remetente, senha)
        servidor.sendmail(remetente, email_destino, mensagem.as_string())

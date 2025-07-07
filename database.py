# database.py
import sqlite3
from datetime import datetime

def criar_tabela_usuarios():
    conn = sqlite3.connect('tarefas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL 
        )
    ''')
    conn.commit()
    conn.close()

def adicionar_usuario_inicial():
    conn = sqlite3.connect('tarefas.db')
    cursor = conn.cursor()
    # Verifica se já existe algum usuário para evitar duplicação
    cursor.execute('SELECT COUNT(*) FROM usuarios')
    count = cursor.fetchone()[0]
    if count == 0:
        # Adiciona um usuário de exemplo com senha em texto puro
        # NOVAMENTE: ISSO É ALTAMENTE INSEGURO PARA PRODUÇÃO
        cursor.execute('INSERT INTO usuarios (username, password) VALUES (?, ?)',
                       ('admin', 'senha123')) # <-- USUÁRIO E SENHA DE EXEMPLO (TEXTO PURO)
        conn.commit()
        print("Usuário inicial 'admin' adicionado com senha em texto puro.")
    conn.close()

def criar_tabela_tarefas():
    conn = sqlite3.connect('tarefas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            data_criacao TEXT NOT NULL,
            data_prevista TEXT,
            data_encerramento TEXT,
            situacao TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def popular_tabela_tarefas():
    conn = sqlite3.connect('tarefas.db')
    cursor = conn.cursor()
    # Verifica se a tabela de tarefas já está populada
    cursor.execute('SELECT COUNT(*) FROM tarefas')
    count = cursor.fetchone()[0]
    if count == 0:
        tarefas = [
            ('Comprar mantimentos', '2023-10-26', '2023-10-28', None, 'Pendente'),
            ('Estudar Python', '2023-10-26', '2023-11-05', None, 'Em andamento'),
            ('Pagar contas', '2023-10-27', '2023-10-27', '2023-10-28', 'Concluído'),
            ('Agendar consulta médica', '2023-10-28', '2023-11-10', None, 'Pendente'),
            ('Ler livro', '2023-10-29', '2023-11-15', None, 'Em andamento'),
            ('Ligar para o banco', '2023-10-30', '2023-10-30', '2023-10-30', 'Concluído'),
            ('Fazer exercícios', '2023-10-31', '2023-11-20', None, 'Pendente'),
            ('Revisar apresentação', '2023-11-01', '2023-11-03', None, 'Em andamento'),
            ('Enviar email', '2023-11-02', '2023-11-02', '2023-11-02', 'Concluído'),
            ('Organizar arquivos', '2023-11-03', '2023-11-25', None, 'Pendente')
        ]
        cursor.executemany('''
            INSERT INTO tarefas (descricao, data_criacao, data_prevista, data_encerramento, situacao)
            VALUES (?, ?, ?, ?, ?)
        ''', tarefas)
        conn.commit()
        print("Tabela de tarefas populada.")
    conn.close()

# Ao executar este arquivo diretamente, ele cria e popula a tabela
if __name__ == '__main__':
    criar_tabela_tarefas()
    popular_tabela_tarefas()
# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, g
import sqlite3
from datetime import datetime
from functools import wraps
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io
import os

#
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_para_sessao'

# Detecta ambiente e define nome do banco
env = os.environ.get("ENV", "desconhecido")
app.config['ENV'] = env
db_filename = f"tarefas_{env}.db"

# Cria banco inicial com usuários e tarefas
def inicializar_banco():
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()

    # Tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Insere admin padrão
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", ('admin', 'admin'))

    # Tabela de tarefas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            data_criacao TEXT,
            data_prevista TEXT,
            data_encerramento TEXT,
            situacao TEXT
        )
    ''')

    conn.commit()
    conn.close()

inicializar_banco()

# Conexão com o banco
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(db_filename)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Funções de Acesso ao Banco de Dados (CRUD Tarefas) ---
def obter_tarefas(filtro_descricao=None, filtro_situacao=None):
    conn = get_db()
    cursor = conn.cursor()
    sql_query = 'SELECT * FROM tarefas WHERE 1=1'
    params = []
    if filtro_descricao:
        sql_query += ' AND descricao LIKE ?'
        params.append('%' + filtro_descricao + '%')
    if filtro_situacao:
        sql_query += ' AND situacao = ?'
        params.append(filtro_situacao)
    cursor.execute(sql_query, params)
    tarefas = cursor.fetchall()

    tarefas_convertidas = []
    for t in tarefas:
        # Converte strings de data para datetime, se não for None
        data_criacao = datetime.strptime(t['data_criacao'], '%Y-%m-%d') if t['data_criacao'] else None
        data_prevista = datetime.strptime(t['data_prevista'], '%Y-%m-%d') if t['data_prevista'] else None
        data_encerramento = datetime.strptime(t['data_encerramento'], '%Y-%m-%d') if t['data_encerramento'] else None

        tarefas_convertidas.append({
            'id': t['id'],
            'descricao': t['descricao'],
            'data_criacao': data_criacao,
            'data_prevista': data_prevista,
            'data_encerramento': data_encerramento,
            'situacao': t['situacao']
        })
    return tarefas_convertidas

def adicionar_tarefa_db(descricao, data_prevista):
    conn = get_db()
    cursor = conn.cursor()
    data_criacao = datetime.now().strftime('%Y-%m-%d')
    situacao = 'Pendente'
    cursor.execute('''
        INSERT INTO tarefas (descricao, data_criacao, data_prevista, situacao)
        VALUES (?, ?, ?, ?)
    ''', (descricao, data_criacao, data_prevista, situacao))
    conn.commit()
    return cursor.lastrowid

def obter_tarefa_por_id(id_tarefa):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tarefas WHERE id = ? LIMIT 1', (id_tarefa,))
    t = cursor.fetchone()
    if not t:
        return None
    data_criacao = datetime.strptime(t['data_criacao'], '%Y-%m-%d') if t['data_criacao'] else None
    data_prevista = datetime.strptime(t['data_prevista'], '%Y-%m-%d') if t['data_prevista'] else None
    data_encerramento = datetime.strptime(t['data_encerramento'], '%Y-%m-%d') if t['data_encerramento'] else None

    return {
        'id': t['id'],
        'descricao': t['descricao'],
        'data_criacao': data_criacao,
        'data_prevista': data_prevista,
        'data_encerramento': data_encerramento,
        'situacao': t['situacao']
    }

def atualizar_tarefa_db(id_tarefa, descricao, data_prevista, data_encerramento, situacao):
    conn = get_db()
    cursor = conn.cursor()
    # Como data_encerramento pode ser None, insira NULL no DB
    cursor.execute('''
        UPDATE tarefas
        SET descricao = ?, data_prevista = ?, data_encerramento = ?, situacao = ?
        WHERE id = ?
    ''', (descricao, data_prevista, data_encerramento, situacao, id_tarefa))
    conn.commit()

def excluir_tarefa_db(id_tarefa):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tarefas WHERE id = ?', (id_tarefa,))
    conn.commit()

# --- Funções de acesso para usuários ---
def verificar_usuario(username, password):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM usuarios WHERE username = ? AND password = ? LIMIT 1', (username, password))
    usuario = cursor.fetchone()
    return usuario is not None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rotas ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if verificar_usuario(username, password):
            session['logged_in'] = True
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('listar_tarefas'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def listar_tarefas():
    filtro_descricao = request.args.get('filtro_descricao')
    filtro_situacao = request.args.get('filtro_situacao')
    tarefas = obter_tarefas(filtro_descricao=filtro_descricao, filtro_situacao=filtro_situacao)
    return render_template('listar_tarefas.html',
                           tarefas=tarefas,
                           filtro_descricao=filtro_descricao,
                           filtro_situacao=filtro_situacao)

@app.route('/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_tarefa():
    if request.method == 'POST':
        descricao = request.form['descricao']
        data_prevista = request.form['data_prevista']  # string YYYY-MM-DD
        adicionar_tarefa_db(descricao, data_prevista)
        flash('Tarefa adicionada com sucesso!', 'success')
        return redirect(url_for('listar_tarefas'))
    return render_template('adicionar_tarefa.html')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_tarefa(id):
    tarefa = obter_tarefa_por_id(id)
    if not tarefa:
        flash('Tarefa não encontrada!', 'danger')
        return redirect(url_for('listar_tarefas'))

    if request.method == 'POST':
        descricao = request.form['descricao']
        data_prevista = request.form['data_prevista']
        data_encerramento = request.form.get('data_encerramento') or None
        situacao = request.form['situacao']
        atualizar_tarefa_db(id, descricao, data_prevista, data_encerramento, situacao)
        flash('Tarefa atualizada com sucesso!', 'success')
        return redirect(url_for('listar_tarefas'))
    return render_template('editar_tarefa.html', tarefa=tarefa)

@app.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_tarefa(id):
    excluir_tarefa_db(id)
    flash('Tarefa excluída com sucesso!', 'success')
    return redirect(url_for('listar_tarefas'))

@app.route('/exportar-pdf')
@login_required
def exportar_pdf():
    filtro_descricao = request.args.get('filtro_descricao')
    filtro_situacao = request.args.get('filtro_situacao')

    tarefas = obter_tarefas(filtro_descricao=filtro_descricao, filtro_situacao=filtro_situacao)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    try:
        h1_style = styles['H1']
    except KeyError:
        h1_style = ParagraphStyle(
            name='FallbackH1', fontSize=18, leading=22, spaceAfter=12, bold=True, alignment=1
        )
    elements.append(Paragraph("Lista de Tarefas", h1_style))

    filter_info = "Filtros: "
    if filtro_descricao:
        filter_info += f"Descrição contendo '{filtro_descricao}'. "
    if filtro_situacao:
        filter_info += f"Situação: '{filtro_situacao}'. "

    try:
        normal_style = styles['Normal']
    except KeyError:
        normal_style = ParagraphStyle(
            name='FallbackNormal', fontSize=10, leading=12, spaceAfter=6,
        )

    if filter_info != "Filtros: ":
        elements.append(Paragraph(filter_info, normal_style))
        elements.append(Paragraph("<br/><br/>", normal_style))

    data = [["ID", "Descrição", "Criação", "Prevista", "Encerramento", "Situação"]]
    for tarefa in tarefas:
        # Formatar datas para string para exibir no PDF (exemplo: '2023-10-31' ou vazio)
        data_criacao = tarefa['data_criacao'].strftime('%Y-%m-%d') if tarefa['data_criacao'] else ''
        data_prevista = tarefa['data_prevista'].strftime('%Y-%m-%d') if tarefa['data_prevista'] else ''
        data_encerramento = tarefa['data_encerramento'].strftime('%Y-%m-%d') if tarefa['data_encerramento'] else ''
        data.append([
            str(tarefa['id']),
            tarefa['descricao'],
            data_criacao,
            data_prevista,
            data_encerramento,
            tarefa['situacao']
        ])

    table = Table(data)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (1, 1), (1, -1), True),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ])
    table.setStyle(style)
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='lista_de_tarefas_filtrada.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

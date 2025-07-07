# test_app.py
import pytest
import sqlite3
import io # Pode ser útil para testes de PDF, mas vamos focar no CRUD por enquanto
from app import app # Importa a instância do seu app Flask
# Importa as funções do banco de dados, vamos adaptá-las para usar a conexão em memória
from database import criar_tabela_usuarios, adicionar_usuario_inicial, criar_tabela_tarefas, popular_tabela_tarefas


# Fixture que configura o cliente de teste e o banco de dados em memória
@pytest.fixture
def client():
    # Usa um banco de dados SQLite em memória para testes
    db_conn = sqlite3.connect(':memory:')

    # Cria um cursor para executar comandos SQL no banco de dados em memória
    cursor = db_conn.cursor()

    # Adapta as funções de criação e população do banco de dados
    # para usarem a conexão em memória APENAS durante o teste
    def criar_tabela_usuarios_test():
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        db_conn.commit()

    def adicionar_usuario_inicial_test():
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.execute('INSERT INTO usuarios (username, password) VALUES (?, ?)',
                           ('admin', 'senha123')) # Usuário de teste com senha em texto puro
            db_conn.commit()

    def criar_tabela_tarefas_test():
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
        db_conn.commit()

    def popular_tabela_tarefas_test():
        cursor.execute('SELECT COUNT(*) FROM tarefas')
        count = cursor.fetchone()[0]
        if count == 0:
            tarefas = [
                ('Tarefa 1', '2024-01-01', '2024-01-05', None, 'Pendente'),
                ('Tarefa 2', '2024-01-01', '2024-01-06', None, 'Em andamento'),
                ('Tarefa 3', '2024-01-02', '2024-01-07', '2024-01-07', 'Concluído'),
            ]
            cursor.executemany('''
                INSERT INTO tarefas (descricao, data_criacao, data_prevista, data_encerramento, situacao)
                VALUES (?, ?, ?, ?, ?)
            ''', tarefas)
            db_conn.commit()


    # Sobrescreve temporariamente a função sqlite3.connect usada no app.py
    # para que ela use a conexão em memória durante os testes
    # Isso é uma abordagem simples para este caso. Em projetos maiores,
    # pode ser melhor usar padrões como injeção de dependência ou ORMs.
    original_connect = sqlite3.connect
    sqlite3.connect = lambda db_name: db_conn

    # Configura o app Flask para modo de teste e define uma chave secreta
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'testing_secret_key' # Chave necessária para a sessão

    # Cria as tabelas e popula com dados de teste no banco em memória
    criar_tabela_usuarios_test()
    adicionar_usuario_inicial_test()
    criar_tabela_tarefas_test()
    popular_tabela_tarefas_test()


    # Cria o cliente de teste do Flask
    with app.test_client() as client:
        yield client # Fornece o cliente de teste para as funções de teste

    # Após o teste, fecha a conexão com o banco em memória e restaura a função original de connect
    db_conn.close()
    sqlite3.connect = original_connect


# Função auxiliar para simular o login no cliente de teste
def login(client, username, password):
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True) # follow_redirects segue o redirecionamento após o POST

# Função auxiliar para simular o logout no cliente de teste
def logout(client):
    return client.get('/logout', follow_redirects=True)


# --- Testes Unitários (20 Cenários) ---

# Testes de Autenticação (Login/Logout) - 4 testes

# 1. Testar que a página de login carrega com sucesso (GET /login)
def test_1_login_page_loads(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'<h1>Login</h1>' in response.data # Verifica se o título da página está no HTML

# 2. Testar login com credenciais válidas redireciona para a lista de tarefas
def test_2_login_valid_credentials_redirects_to_list(client):
    response = login(client, 'admin', 'senha123')
    assert response.status_code == 200 # O redirecionamento foi seguido, então deve ser 200 da página de destino
    assert b'Login bem-sucedido!' in response.data # Verifica a mensagem flash de sucesso
    assert b'Lista de Tarefas' in response.data # Verifica se o conteúdo da página de lista está presente

# 3. Testar login com credenciais inválidas re-renderiza a página de login e mostra erro
def test_3_login_invalid_credentials_stays_on_login(client):
    response = login(client, 'admin', 'senha_errada')
    assert response.status_code == 200 # Re-renderiza a página de login (não redireciona para outro lugar)
    assert b'Usu\xc3\xa1rio ou senha inv\xc3\xa1lidos.' in response.data # Verifica a mensagem flash de erro (lidar com acentos)
    assert b'<h1>Login</h1>' in response.data # Verifica se ainda está na página de login

# 4. Testar logout redireciona para a página de login
def test_4_logout_redirects_to_login(client):
    login(client, 'admin', 'senha123') # Loga primeiro
    response = logout(client)
    assert response.status_code == 200 # Segue o redirecionamento para a página de login
    assert b'Voc\xc3\xaa foi desconectado.' in response.data # Verifica a mensagem flash de logout (lidar com acentos)
    assert b'<h1>Login</h1>' in response.data # Verifica se está na página de login

# Testes de Controle de Acesso (@login_required) - 4 testes

# 5. Testar GET / (listar tarefas) redireciona para login quando deslogado
def test_5_list_tasks_redirects_to_login_when_not_logged_in(client):
    response = client.get('/', follow_redirects=False) # Não segue o redirecionamento
    assert response.status_code == 302 # Verifica se houve um redirecionamento (302 Found)
    assert '/login' in response.headers['Location'] # Verifica se a URL de redirecionamento é /login

# 6. Testar GET /adicionar (adicionar tarefa) redireciona para login quando deslogado
def test_6_add_task_get_redirects_to_login_when_not_logged_in(client):
    response = client.get('/adicionar', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

# 7. Testar GET /editar/1 (editar tarefa) redireciona para login quando deslogado
def test_7_edit_task_get_redirects_to_login_when_not_logged_in(client):
    response = client.get('/editar/1', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

# 8. Testar POST /excluir/1 (excluir tarefa) redireciona para login quando deslogado
def test_8_delete_task_post_redirects_to_login_when_not_logged_in(client):
    response = client.post('/excluir/1', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

# Testes de Leitura (Listar e Obter Individual) - 3 testes

# 9. Testar GET / (listar tarefas) carrega com sucesso e mostra tarefas quando logado
def test_9_list_tasks_loads_when_logged_in(client):
    login(client, 'admin', 'senha123')
    response = client.get('/')
    assert response.status_code == 200
    assert b'Lista de Tarefas' in response.data
    assert b'Tarefa 1' in response.data # Verifica se as tarefas populares est\xc3\xa3o l\xc3\xa1 (lidar com acentos)
    assert b'Tarefa 2' in response.data
    assert b'Tarefa 3' in response.data

# 10. Testar GET /editar/<id> carrega o formul\xc3\xa1rio com dados da tarefa existente quando logado
def test_10_edit_task_get_loads_form_with_data_when_logged_in(client):
    login(client, 'admin', 'senha123')
    # Vamos pegar a Task 1 (ID 1)
    response = client.get('/editar/1')
    assert response.status_code == 200
    assert b'<h1>Editar Tarefa</h1>' in response.data
    assert b'Tarefa 1' in response.data # Verifica se a descri\xc3\xa7\xc3\xa3o est\xc3\xa1 pr\xc3\xa9-preenchida (lidar com acentos)
    assert b'2024-01-05' in response.data # Verifica se a data prevista est\xc3\xa1 pr\xc3\xa9-preenchida

# 11. Testar GET /editar/<invalid_id> redireciona para a lista com mensagem de erro quando logado
def test_11_edit_task_get_invalid_id_redirects_with_error(client):
    login(client, 'admin', 'senha123')
    response = client.get('/editar/999', follow_redirects=True) # Assumindo que o ID 999 n\xc3\xa3o existe
    assert response.status_code == 200 # Segue o redirecionamento para a lista
    assert b'Tarefa n\xc3\xa3o encontrada!' in response.data # Verifica a mensagem flash (lidar com acentos)
    assert b'Lista de Tarefas' in response.data # Verifica se est\xc3\xa1 na p\xc3\xa1gina de lista

# Testes de Criação (Adicionar Tarefa) - 3 testes

# 12. Testar GET /adicionar carrega o formul\xc3\xa1rio quando logado
def test_12_add_task_get_loads_form_when_logged_in(client):
    login(client, 'admin', 'senha123')
    response = client.get('/adicionar')
    assert response.status_code == 200
    assert b'<h1>Adicionar Nova Tarefa</h1>' in response.data

# 13. Testar POST /adicionar adiciona uma tarefa e redireciona para a lista quando logado
def test_13_add_task_post_adds_task_and_redirects(client):
    login(client, 'admin', 'senha123')
    task_data = {
        'descricao': 'Nova Tarefa Teste Add',
        'data_prevista': '2025-01-10'
    }
    response = client.post('/adicionar', data=task_data, follow_redirects=True)
    assert response.status_code == 200 # Segue o redirecionamento para a lista
    assert b'Tarefa adicionada com sucesso!' in response.data # Verifica mensagem flash
    assert b'Lista de Tarefas' in response.data # Verifica que est\xc3\xa1 na p\xc3\xa1gina de lista

# 14. Testar que a tarefa adicionada via POST aparece na lista
def test_14_added_task_appears_in_list(client):
    login(client, 'admin', 'senha123')
    task_data = {
        'descricao': 'Tarefa Recem Adicionada',
        'data_prevista': '2025-02-15'
    }
    client.post('/adicionar', data=task_data, follow_redirects=True) # Adiciona a tarefa

    # Agora faz um GET na lista para verificar se a tarefa est\xc3\xa1 l\xc3\xa1
    response = client.get('/')
    assert response.status_code == 200
    assert b'Tarefa Recem Adicionada' in response.data # Verifica se a descri\xc3\xa7\xc3\xa3o aparece na p\xc3\xa1gina

# Testes de Atualização (Editar Tarefa) - 4 testes

# 15. Testar GET /editar/<id> carrega o formul\xc3\xa1rio com dados da tarefa existente quando logado
def test_15_edit_task_get_loads_form_existing(client):
    login(client, 'admin', 'senha123')
    response = client.get('/editar/1')
    assert response.status_code == 200
    assert b'Tarefa 1' in response.data

# 16. Testar GET /editar/<invalid_id> redireciona para a lista com mensagem de erro quando logado
# (Este teste \xc3\xa9 o mesmo que o teste 11, mas \xc3\xa9 bom para ter em conta o count)
def test_16_edit_task_get_invalid_id_redirects(client):
     login(client, 'admin', 'senha123')
     response = client.get('/editar/999', follow_redirects=True)
     assert response.status_code == 200
     assert b'Tarefa n\xc3\xa3o encontrada!' in response.data


# 17. Testar POST /editar/<id> atualiza a tarefa e redireciona para a lista quando logado
def test_17_edit_task_post_updates_task_and_redirects(client):
    login(client, 'admin', 'senha123')
    # Dados para atualizar a Task 1 (ID 1)
    updated_data = {
        'descricao': 'Tarefa 1 Editada',
        'data_prevista': '2024-01-15',
        'data_encerramento': '2024-01-14',
        'situacao': 'Conclu\xc3\xaddo' # Lidar com acento
    }
    response = client.post('/editar/1', data=updated_data, follow_redirects=True)
    assert response.status_code == 200 # Segue o redirecionamento
    assert b'Tarefa atualizada com sucesso!' in response.data # Verifica mensagem flash
    assert b'Lista de Tarefas' in response.data # Verifica que est\xc3\xa1 na p\xc3\xa1gina de lista

# 18. Testar que a tarefa atualizada via POST mostra os novos dados na lista
def test_18_updated_task_shows_new_data_in_list(client):
    login(client, 'admin', 'senha123')
    # Primeiro, atualiza a Task 1 (ID 1)
    updated_data = {
        'descricao': 'Tarefa Um Modificada',
        'data_prevista': '2024-02-20',
        'data_encerramento': '2024-02-19',
        'situacao': 'Em andamento'
    }
    client.post('/editar/1', data=updated_data) # N\xc3\xa3o segue o redirecionamento ainda

    # Agora faz um GET na lista para verificar os dados atualizados
    response = client.get('/')
    assert response.status_code == 200
    assert b'Tarefa Um Modificada' in response.data
    assert b'2024-02-20' in response.data
    assert b'2024-02-19' in response.data
    assert b'Em andamento' in response.data

# Testes de Exclusão (Remover Tarefa) - 2 testes

# 19. Testar POST /excluir/<id> exclui a tarefa e redireciona para a lista quando logado
def test_19_delete_task_post_deletes_task_and_redirects(client):
    login(client, 'admin', 'senha123')
    # Vamos excluir a Task 1 (ID 1)
    response = client.post('/excluir/1', follow_redirects=True)
    assert response.status_code == 200 # Segue o redirecionamento
    assert b'Tarefa exclu\xc3\xadda com sucesso!' in response.data # Verifica mensagem flash (lidar com acentos)
    assert b'Lista de Tarefas' in response.data # Verifica que est\xc3\xa1 na p\xc3\xa1gina de lista

# 20. Testar que a tarefa exclu\xc3\xadda via POST n\xc3\xa3o aparece mais na lista
def test_20_deleted_task_is_not_in_list(client):
    login(client, 'admin', 'senha123')
    # Primeiro, exclui a Task 2 (ID 2)
    client.post('/excluir/2') # N\xc3\xa3o segue o redirecionamento ainda

    # Agora faz um GET na lista para verificar se a tarefa sumiu
    response = client.get('/')
    assert response.status_code == 200
    assert b'Tarefa 2' not in response.data # Verifica se a descri\xc3\xa7\xc3\xa3o n\xc3\xa3o aparece na p\xc3\xa1gina
import os
import asyncio
import json
import time
import hashlib
from datetime import datetime
import aiosqlite
import aiohttp
from aiohttp import web
import jinja2
import aiohttp_jinja2

# Configurações
DB_PATH = "chat.db"
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Cria diretório static se não existir (não usado, mas mantido por compatibilidade)
os.makedirs(STATIC_DIR, exist_ok=True)

# Template HTML embutido
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>global chat By Tz</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body {
            background: #1e1f22;
            color: #dcddde;
            height: 100vh;
            overflow: hidden;
            display: none;
        }
        .loading {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            transition: opacity 0.5s;
        }
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid rgba(220, 221, 222, 0.3);
            border-top: 4px solid #7289da;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .auth-container {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            background: #2f3136;
            padding: 30px;
            border-radius: 8px;
            width: 90%;
            max-width: 400px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        .auth-container h2 { text-align: center; margin-bottom: 20px; color: #fff; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #b9bbbe; }
        .form-group input {
            width: 100%;
            padding: 10px;
            background: #36393f;
            border: 1px solid #4f545c;
            border-radius: 4px;
            color: #dcddde;
        }
        .form-group input:focus {
            outline: none;
            border-color: #7289da;
        }
        .btn {
            width: 100%;
            padding: 10px;
            background: #7289da;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            margin-top: 10px;
        }
        .btn:hover { background: #677bc4; }
        .switch-form { text-align: center; margin-top: 15px; color: #b9bbbe; }
        .switch-form a { color: #7289da; text-decoration: none; cursor: pointer; }

        .chat-container {
            display: none;
            height: 100vh;
            background: #36393f;
        }
        .chat-header {
            padding: 12px 16px;
            background: #2f3136;
            border-bottom: 1px solid #4f545c;
            font-weight: bold;
            color: #fff;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .main-content {
            display: flex;
            height: calc(100% - 50px);
        }
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 16px;
        }
        #messages {
            flex: 1;
            overflow-y: auto;
            padding-bottom: 10px;
        }
        .message {
            margin-bottom: 12px;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .message-author { font-weight: bold; color: #7289da; }
        .message-time { color: #72767d; font-size: 0.85em; margin-left: 8px; }
        .message-text { margin-top: 4px; color: #dcddde; }

        .members-panel {
            width: 240px;
            background: #2f3136;
            border-left: 1px solid #4f545c;
            padding: 16px 12px;
            overflow-y: auto;
        }
        .members-panel h3 {
            color: #b9bbbe;
            margin-bottom: 12px;
            font-size: 1em;
        }
        .member {
            padding: 6px 8px;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            margin-bottom: 4px;
        }
        .member:hover { background: #36393f; }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .online { background: #43b581; }
        .offline { background: #747f8d; }

        #message-input {
            width: 100%;
            padding: 10px;
            background: #40444b;
            border: none;
            border-radius: 4px;
            color: #dcddde;
            margin-top: 10px;
        }
        #message-input:focus { outline: none; }

        .profile-modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            background: #2f3136;
            padding: 20px;
            border-radius: 8px;
            width: 90%;
            max-width: 400px;
            color: #dcddde;
        }
        .modal-content h3 { margin-bottom: 15px; }
        .close-modal { float: right; cursor: pointer; color: #b9bbbe; }
    </style>
</head>
<body>

<div class="loading" id="loading">
    <div class="spinner"></div>
</div>

<div class="auth-container" id="loginForm">
    <h2>Login</h2>
    <div class="form-group">
        <label for="login-name">DisplayName</label>
        <input type="text" id="login-name" placeholder="Seu DisplayName">
    </div>
    <div class="form-group">
        <label for="login-pass">Senha</label>
        <input type="password" id="login-pass" placeholder="Sua senha">
    </div>
    <button class="btn" onclick="login()">Entrar</button>
    <div class="switch-form">Não tem conta? <a onclick="showRegister()">Cadastre-se</a></div>
</div>

<div class="auth-container" id="registerForm" style="display:none;">
    <h2>Cadastro</h2>
    <div class="form-group">
        <label for="reg-first">Nome Real</label>
        <input type="text" id="reg-first" placeholder="Seu nome">
    </div>
    <div class="form-group">
        <label for="reg-display">DisplayName</label>
        <input type="text" id="reg-display" placeholder="DisplayName único">
    </div>
    <div class="form-group">
        <label for="reg-pass">Senha</label>
        <input type="password" id="reg-pass" placeholder="Senha">
    </div>
    <div class="form-group">
        <label for="reg-pass2">Confirmar Senha</label>
        <input type="password" id="reg-pass2" placeholder="Confirme a senha">
    </div>
    <button class="btn" onclick="register()">Cadastrar</button>
    <div class="switch-form">Já tem conta? <a onclick="showLogin()">Faça login</a></div>
</div>

<div class="chat-container" id="chatApp">
    <div class="chat-header">
        <span>global chat By Tz</span>
        <span id="userDisplay" style="cursor:pointer;" onclick="openProfile()"></span>
    </div>
    <div class="main-content">
        <div class="chat-area">
            <div id="messages"></div>
            <input type="text" id="message-input" placeholder="Digite sua mensagem..." onkeypress="handleKeyPress(event)">
        </div>
        <div class="members-panel">
            <h3>Membros (<span id="memberCount">0</span>)</h3>
            <div id="membersList"></div>
        </div>
    </div>
</div>

<div class="profile-modal" id="profileModal">
    <div class="modal-content">
        <span class="close-modal" onclick="closeProfile()">&times;</span>
        <h3>Meu Perfil</h3>
        <p><strong>Nome:</strong> <span id="profileFirstName"></span></p>
        <div class="form-group">
            <label for="editDisplay">DisplayName</label>
            <input type="text" id="editDisplay" placeholder="Novo DisplayName">
        </div>
        <button class="btn" onclick="updateDisplayName()">Atualizar DisplayName</button>
    </div>
</div>

<script>
    let ws = null;
    let currentUser = null;

    function show(elementId) {
        document.querySelectorAll('.auth-container, #chatApp').forEach(el => el.style.display = 'none');
        document.getElementById(elementId).style.display = 'block';
    }

    function showLogin() { show('loginForm'); }
    function showRegister() { show('registerForm'); }

    async function login() {
        const name = document.getElementById('login-name').value.trim();
        const pass = document.getElementById('login-pass').value;
        if (!name || !pass) return alert("Preencha todos os campos!");
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ display_name: name, password: pass })
        });
        const data = await res.json();
        if (data.success) {
            currentUser = data.user;
            connectWebSocket();
        } else {
            alert(data.message || "Erro no login");
        }
    }

    async function register() {
        const first = document.getElementById('reg-first').value.trim();
        const display = document.getElementById('reg-display').value.trim();
        const pass1 = document.getElementById('reg-pass').value;
        const pass2 = document.getElementById('reg-pass2').value;
        if (!first || !display || !pass1 || !pass2) return alert("Preencha todos os campos!");
        if (pass1 !== pass2) return alert("Senhas não coincidem!");
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ first_name: first, display_name: display, password: pass1 })
        });
        const data = await res.json();
        if (data.success) {
            alert("Cadastro realizado! Faça login.");
            showLogin();
        } else {
            alert(data.message || "Erro no cadastro");
        }
    }

    function connectWebSocket() {
        ws = new WebSocket(`ws://${window.location.host}/ws`);
        ws.onopen = () => {
            ws.send(JSON.stringify({ type: 'auth', user_id: currentUser.id }));
        };
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'message') {
                addMessage(msg.data);
            } else if (msg.type === 'members') {
                updateMembers(msg.data);
            } else if (msg.type === 'init') {
                document.getElementById('loading').style.display = 'none';
                document.body.style.display = 'block';
                show('chatApp');
                document.getElementById('userDisplay').textContent = currentUser.display_name;
                document.getElementById('profileFirstName').textContent = currentUser.first_name;
                document.getElementById('editDisplay').value = currentUser.display_name;
            }
        };
        ws.onclose = () => {
            setTimeout(connectWebSocket, 2000);
        };
    }

    function addMessage({ author, text, timestamp }) {
        const messagesDiv = document.getElementById('messages');
        const div = document.createElement('div');
        div.className = 'message';
        const timeStr = new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        div.innerHTML = `<span class="message-author">${author}</span><span class="message-time">${timeStr}</span><div class="message-text">${escapeHtml(text)}</div>`;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    function updateMembers(members) {
        const list = document.getElementById('membersList');
        const count = document.getElementById('memberCount');
        list.innerHTML = '';
        count.textContent = members.length;
        members.forEach(m => {
            const div = document.createElement('div');
            div.className = 'member';
            div.innerHTML = `<span class="status-dot ${m.online ? 'online' : 'offline'}"></span>${m.display_name}`;
            list.appendChild(div);
        });
    }

    function handleKeyPress(e) {
        if (e.key === 'Enter') {
            const input = document.getElementById('message-input');
            if (input.value.trim()) {
                ws.send(JSON.stringify({ type: 'message', text: input.value }));
                input.value = '';
            }
        }
    }

    function openProfile() {
        document.getElementById('profileModal').style.display = 'flex';
    }

    function closeProfile() {
        document.getElementById('profileModal').style.display = 'none';
    }

    async function updateDisplayName() {
        const newDisplay = document.getElementById('editDisplay').value.trim();
        if (!newDisplay) return alert("DisplayName não pode estar vazio!");
        const res = await fetch('/api/update_display', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: currentUser.id, new_display: newDisplay })
        });
        const data = await res.json();
        if (data.success) {
            currentUser.display_name = newDisplay;
            document.getElementById('userDisplay').textContent = newDisplay;
            closeProfile();
            // Notifica o servidor para atualizar membros
            ws.send(JSON.stringify({ type: 'refresh_members' }));
        } else {
            alert(data.message);
        }
    }

    function escapeHtml(text) {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    // Simula loading por 1 segundo
    setTimeout(() => {
        document.getElementById('loading').style.opacity = '0';
        setTimeout(() => {
            document.getElementById('loading').style.display = 'none';
            document.body.style.display = 'block';
        }, 500);
    }, 1000);
</script>
</body>
</html>
'''

# Funções auxiliares
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                display_name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                last_seen REAL
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                timestamp REAL NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        await db.commit()

# Rotas HTTP
@aiohttp_jinja2.template("index.html")
async def index(request):
    return {}

async def api_register(request):
    data = await request.json()
    first_name = data.get('first_name', '').strip()
    display_name = data.get('display_name', '').strip()
    password = data.get('password', '')

    if not first_name or not display_name or not password:
        return web.json_response({"success": False, "message": "Todos os campos são obrigatórios."})

    async with aiosqlite.connect(DB_PATH) as db:
        # Verifica se o display_name já existe (case-insensitive)
        async with db.execute("SELECT 1 FROM users WHERE display_name = ?", (display_name,)) as cursor:
            if await cursor.fetchone():
                return web.json_response({"success": False, "message": "DisplayName já está em uso."})

        password_hash = hash_password(password)
        await db.execute(
            "INSERT INTO users (first_name, display_name, password_hash, last_seen) VALUES (?, ?, ?, ?)",
            (first_name, display_name, password_hash, time.time())
        )
        await db.commit()
        return web.json_response({"success": True})

async def api_login(request):
    data = await request.json()
    display_name = data.get('display_name', '').strip()
    password = data.get('password', '')
    if not display_name or not password:
        return web.json_response({"success": False, "message": "Campos obrigatórios."})

    password_hash = hash_password(password)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, first_name, display_name FROM users WHERE display_name = ? AND password_hash = ?",
            (display_name, password_hash)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                user = {"id": row[0], "first_name": row[1], "display_name": row[2]}
                # Atualiza last_seen
                await db.execute("UPDATE users SET last_seen = ? WHERE id = ?", (time.time(), row[0]))
                await db.commit()
                return web.json_response({"success": True, "user": user})
            else:
                return web.json_response({"success": False, "message": "DisplayName ou senha incorretos."})

async def api_update_display(request):
    data = await request.json()
    user_id = data.get('user_id')
    new_display = data.get('new_display', '').strip()

    if not user_id or not new_display:
        return web.json_response({"success": False, "message": "Dados inválidos."})

    async with aiosqlite.connect(DB_PATH) as db:
        # Verifica se já existe outro com esse display
        async with db.execute("SELECT 1 FROM users WHERE display_name = ? AND id != ?", (new_display, user_id)) as cursor:
            if await cursor.fetchone():
                return web.json_response({"success": False, "message": "DisplayName já está em uso."})

        await db.execute("UPDATE users SET display_name = ? WHERE id = ?", (new_display, user_id))
        await db.commit()
        return web.json_response({"success": True})

# WebSocket
websockets = {}  # user_id -> set of ws

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    user_id = None
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data['type'] == 'auth':
                    user_id = data['user_id']
                    websockets[user_id] = ws
                    # Envia histórico de mensagens
                    history = []
                    async with aiosqlite.connect(DB_PATH) as db:
                        async with db.execute(
                            "SELECT u.display_name, m.text, m.timestamp FROM messages m JOIN users u ON m.user_id = u.id ORDER BY m.timestamp DESC LIMIT 100"
                        ) as cursor:
                            rows = await cursor.fetchall()
                            history = [{"author": r[0], "text": r[1], "timestamp": r[2]} for r in reversed(rows)]
                    # Envia membros
                    members = []
                    async with aiosqlite.connect(DB_PATH) as db:
                        now = time.time()
                        async with db.execute("SELECT id, display_name, last_seen FROM users") as cursor:
                            async for row in cursor:
                                uid, dname, last = row
                                online = (now - last) < 60  # offline após 60s
                                members.append({"id": uid, "display_name": dname, "online": online})
                    await ws.send_json({"type": "init"})
                    for m in history:
                        await ws.send_json({"type": "message", "data": m})
                    await ws.send_json({"type": "members", "data": members})
                elif data['type'] == 'message' and user_id:
                    text = data['text'].strip()
                    if text:
                        timestamp = time.time()
                        async with aiosqlite.connect(DB_PATH) as db:
                            await db.execute(
                                "INSERT INTO messages (user_id, text, timestamp) VALUES (?, ?, ?)",
                                (user_id, text, timestamp)
                            )
                            await db.commit()
                        # Busca display_name do remetente
                        async with aiosqlite.connect(DB_PATH) as db:
                            async with db.execute("SELECT display_name FROM users WHERE id = ?", (user_id,)) as cursor:
                                row = await cursor.fetchone()
                                author = row[0] if row else "Desconhecido"
                        message_data = {"author": author, "text": text, "timestamp": timestamp}
                        # Envia para todos
                        to_remove = []
                        for uid, w in websockets.items():
                            try:
                                await w.send_json({"type": "message", "data": message_data})
                            except:
                                to_remove.append(uid)
                        for uid in to_remove:
                            websockets.pop(uid, None)
                elif data['type'] == 'refresh_members' and user_id:
                    members = []
                    async with aiosqlite.connect(DB_PATH) as db:
                        now = time.time()
                        async with db.execute("SELECT id, display_name, last_seen FROM users") as cursor:
                            async for row in cursor:
                                uid, dname, last = row
                                online = (now - last) < 60
                                members.append({"id": uid, "display_name": dname, "online": online})
                    to_remove = []
                    for w in websockets.values():
                        try:
                            await w.send_json({"type": "members", "data": members})
                        except:
                            to_remove.append(uid)
                    for uid in to_remove:
                        websockets.pop(uid, None)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
    finally:
        if user_id:
            websockets.pop(user_id, None)
            # Atualiza last_seen
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET last_seen = ? WHERE id = ?", (time.time(), user_id))
                await db.commit()
    return ws

# Configuração da aplicação
app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.DictLoader({'index.html': HTML_TEMPLATE}))
app.router.add_get('/', index)
app.router.add_post('/api/register', api_register)
app.router.add_post('/api/login', api_login)
app.router.add_post('/api/update_display', api_update_display)
app.router.add_get('/ws', websocket_handler)

# Inicialização
async def main():
    await init_db()
    port = int(os.environ.get('PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Servidor rodando na porta {port}")
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())

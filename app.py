from aiohttp import web, WSMsgType
import sqlite3, json, os

# ======================
# BANCO DE DADOS
# ======================
DB_FILE = "notbebad.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    display_name TEXT,
    first_name TEXT,
    password TEXT,
    status TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    display_name TEXT,
    content TEXT
)
""")
conn.commit()

# ======================
# APP
# ======================
app = web.Application()
clients = set()

# ======================
# HTML
# ======================
HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NotBeBad</title>
<style>
body{margin:0;font-family:sans-serif;background:#121212;color:white;display:flex;height:100vh;}
.sidebar{width:200px;background:#1e1e1e;padding:10px;display:flex;flex-direction:column;}
.logo{text-align:center;font-weight:bold;margin-bottom:10px;color:#9c27b0;}
.member{padding:5px;margin:3px 0;background:#333;cursor:pointer;}
.main{flex:1;display:flex;flex-direction:column;}
.chat-container{flex:1;padding:10px;overflow-y:auto;background:#222;}
.message{margin:5px 0;padding:5px;background:#333;border-radius:5px;}
.input-area{display:flex;padding:10px;background:#1e1e1e;}
input[type=text]{flex:1;padding:5px;border-radius:5px;border:none;}
button{padding:5px;margin-left:5px;border:none;border-radius:5px;background:#9c27b0;color:white;cursor:pointer;}
.modal{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);display:flex;justify-content:center;align-items:center;display:none;}
.modal.active{display:flex;}
.modal-content{background:#222;padding:20px;border-radius:10px;width:300px;}
</style>
</head>
<body>

<div class="sidebar">
<div class="logo">NotBeBad</div>
<div id="membersList"></div>
</div>

<div class="main">
<div class="chat-container" id="chatBox"></div>
<div class="input-area">
<input type="text" id="messageInput" placeholder="Mensagem..." onkeypress="if(event.key==='Enter') sendMessage()">
<button onclick="sendMessage()">Enviar</button>
</div>
</div>

<!-- Perfil Modal -->
<div class="modal" id="profileModal">
<div class="modal-content">
<h3>Perfil</h3>
<label>Display Name</label>
<input type="text" id="displayName">
<label>First Name</label>
<input type="text" id="firstName" readonly>
<button onclick="saveProfile()">Salvar</button>
<button onclick="closeModal()">Fechar</button>
</div>
</div>

<!-- Login Modal -->
<div class="modal active" id="loginModal">
<div class="modal-content">
<h3>Crie sua conta</h3>
<label>Display Name</label><input type="text" id="loginDisplay">
<label>First Name</label><input type="text" id="loginFirst">
<label>Senha</label><input type="password" id="loginPass">
<button onclick="createAccount()">Criar</button>
</div>
</div>

<script>
let socket;
let currentUser;

function connectWS(){
    socket = new WebSocket(`ws://${location.host}/ws`);
    socket.onmessage = e => {
        const msg = JSON.parse(e.data);
        const chatBox = document.getElementById("chatBox");
        const div = document.createElement("div");
        div.className = "message";
        div.textContent = `${msg.display_name}: ${msg.content}`;
        chatBox.appendChild(div);
        chatBox.scrollTop = chatBox.scrollHeight;
        loadMembers(); // Atualiza membros dinamicamente
    };
}

async function loadMembers(){
    const res = await fetch("/members");
    const data = await res.json();
    const container = document.getElementById("membersList");
    container.innerHTML = "";
    data.forEach(m=>{
        const div = document.createElement("div");
        div.className="member";
        div.textContent = m.displayName + (m.username===currentUser.username?" (Você)":"");
        div.onclick = () => openProfile(m);
        container.appendChild(div);
    });
}

function openProfile(user){
    document.getElementById("profileModal").classList.add("active");
    document.getElementById("displayName").value = user.displayName;
    document.getElementById("firstName").value = user.firstName;
}

async function saveProfile(){
    const display = document.getElementById("displayName").value.trim();
    await fetch("/update_profile",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({username:currentUser.username,display_name:display})
    });
    document.getElementById("profileModal").classList.remove("active");
    currentUser.display_name = display;
    loadMembers();
}

function closeModal(){document.getElementById("profileModal").classList.remove("active");}

function sendMessage(){
    const input=document.getElementById("messageInput");
    const msg=input.value.trim();
    if(!msg) return;
    socket.send(JSON.stringify({username:currentUser.username,display_name:currentUser.display_name,content:msg}));
    input.value="";
}

async function createAccount(){
    const display=document.getElementById("loginDisplay").value.trim();
    const first=document.getElementById("loginFirst").value.trim();
    const pass=document.getElementById("loginPass").value.trim();
    if(!display||!first||!pass){alert("Preencha todos os campos");return;}
    const res = await fetch("/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({display_name:display,first_name:first,password:pass})});
    const data = await res.json();
    if(data.ok){
        currentUser = {username:display, display_name:display, first_name:first};
        document.getElementById("loginModal").classList.remove("active");
        connectWS();
        loadMembers();
        const msgs = await fetch("/messages").then(r=>r.json());
        const chatBox = document.getElementById("chatBox");
        msgs.forEach(m=>{
            const div = document.createElement("div");
            div.className="message";
            div.textContent=`${m.display_name}: ${m.content}`;
            chatBox.appendChild(div);
        });
    } else {alert("Erro ao criar conta");}
}

</script>
</body>
</html>
"""

# ======================
# ROTAS
# ======================
async def index(request): return web.Response(text=HTML, content_type="text/html")

async def register(request):
    data = await request.json()
    username = data["display_name"]
    cur.execute("INSERT OR IGNORE INTO users (username, display_name, first_name, password, status) VALUES (?,?,?,?,?)",
                (username, data["display_name"], data["first_name"], data["password"], "online"))
    conn.commit()
    return web.json_response({"ok": True})

async def members(request):
    cur.execute("SELECT username, display_name, first_name, status FROM users")
    users = [{"username":u[0],"displayName":u[1],"firstName":u[2],"status":u[3]} for u in cur.fetchall()]
    return web.json_response(users)

async def get_messages(request):
    cur.execute("SELECT username, display_name, content FROM messages")
    msgs = [{"username":u,"display_name":d,"content":c} for u,d,c in cur.fetchall()]
    return web.json_response(msgs)

async def update_profile(request):
    data = await request.json()
    cur.execute("UPDATE users SET display_name=? WHERE username=?", (data["display_name"], data["username"]))
    conn.commit()
    return web.json_response({"ok": True})

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    clients.add(ws)
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                cur.execute("INSERT INTO messages (username, display_name, content) VALUES (?,?,?)",
                            (data["username"], data["display_name"], data["content"]))
                conn.commit()
                for client in clients:
                    await client.send_str(msg.data)
    finally:
        clients.remove(ws)
    return ws

# ======================
# ROTAS
# ======================
app.router.add_get("/", index)
app.router.add_post("/register", register)
app.router.add_get("/members", members)
app.router.add_get("/messages", get_messages)
app.router.add_post("/update_profile", update_profile)
app.router.add_get("/ws", websocket_handler)

# ======================
# RUN
# ======================
web.run_app(app, port=int(os.environ.get("PORT",8080)))

from aiohttp import web
import asyncio
import sqlite3
import json
import os

# ======================
# BANCO DE DADOS
# ======================
DB_FILE = "notbebad.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()

# Usuários
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    display_name TEXT,
    first_name TEXT,
    status TEXT
)
""")
# Mensagens
cur.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
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
# HTML (UI completa do NotBeBad)
# ======================
HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>NotBeBad</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>
<style>
:root {
  --bg-dark:#121212; --bg-darker:#0f0f0f; --accent-purple:#9c27b0;
  --accent-light:#e1bee7; --text-primary:#fff; --text-secondary:#b39ddb;
  --border-color:#333; --card-bg:#1e1e1e; --online:#4caf50; --offline:#9e9e9e;
}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;}
body{background:var(--bg-dark);color:var(--text-primary);overflow:hidden;height:100vh;display:flex;}
.sidebar{width:240px;background:var(--bg-darker);display:flex;flex-direction:column;padding:16px 8px;border-right:1px solid var(--border-color);}
.logo{font-size:20px;font-weight:800;text-align:center;margin-bottom:24px;color:var(--accent-purple);letter-spacing:1px;}
.server-item{padding:10px 12px;border-radius:8px;margin:4px 8px;cursor:pointer;display:flex;align-items:center;gap:10px;background:var(--accent-purple);}
.members-section{margin-top:20px;padding-top:12px;border-top:1px solid var(--border-color);}
.section-header{display:flex;justify-content:space-between;padding:0 16px 8px;}
.section-title{font-size:12px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:1px;}
.member-count{font-size:11px;color:var(--text-secondary);}
.member{display:flex;align-items:center;padding:8px 12px;border-radius:6px;cursor:pointer;position:relative;}
.member:hover{background: rgba(255,255,255,0.05);}
.status-indicator{width:8px;height:8px;border-radius:50%;position:absolute;left:36px;bottom:8px;}
.online{background:var(--online);}
.offline{background:var(--offline);}
.pfp{width:32px;height:32px;border-radius:50%;background:var(--accent-purple);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;position:relative;}
.member-info{margin-left:10px;font-size:14px;}
.main{flex:1;display:flex;flex-direction:column;height:100vh;}
.top-bar{height:48px;background:var(--bg-darker);display:flex;align-items:center;padding:0 16px;border-bottom:1px solid var(--border-color);}
.channel-name{font-weight:600;font-size:16px;}
.chat-container{flex:1;padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:16px;}
.pinned-message{background:rgba(156,39,176,0.15);border-left:4px solid var(--accent-purple);padding:12px;border-radius:8px;font-size:14px;line-height:1.5;}
.message{display:flex;gap:12px;}
.message-content{background:var(--card-bg);padding:10px 14px;border-radius:12px;max-width:70%;}
.input-area{padding:12px 16px;background:var(--bg-darker);display:flex;gap:10px;border-top:1px solid var(--border-color);}
.message-input{flex:1;background:var(--card-bg);border:none;border-radius:24px;padding:10px 16px;color:white;outline:none;}
.send-btn{background:var(--accent-purple);color:white;border:none;width:40px;height:40px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;}
.send-btn:hover{transform:scale(1.1);transition:transform 0.2s;}
.modal-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;opacity:0;visibility:hidden;transition:all 0.3s ease;}
.modal-overlay.active{opacity:1;visibility:visible;}
.profile-modal{background:var(--card-bg);width:90%;max-width:400px;border-radius:16px;padding:24px;position:relative;}
.modal-title{text-align:center;margin-bottom:20px;font-size:20px;color:var(--accent-purple);}
.pfp-large{width:100px;height:100px;border-radius:50%;background:var(--accent-purple);margin:0 auto 20px;display:flex;align-items:center;justify-content:center;color:white;font-size:40px;font-weight:bold;}
.status-badge{position:absolute;top:80px;left:50%;transform:translateX(-50%);width:20px;height:20px;border-radius:50%;border:3px solid var(--card-bg);}
.form-group{margin-bottom:16px;}
.form-group label{display:block;margin-bottom:6px;color:var(--text-secondary);font-size:14px;}
.form-group input{width:100%;background:var(--bg-darker);border:1px solid var(--border-color);border-radius:8px;padding:10px;color:white;}
.btn-group{display:flex;gap:10px;margin-top:20px;}
.btn{flex:1;padding:10px;border:none;border-radius:8px;font-weight:bold;cursor:pointer;}
.btn-save{background:var(--online);color:white;}
.btn-close{background:#f44336;color:white;}
</style>
</head>
<body>
<div class="sidebar">
<div class="logo">NotBeBad</div>
<div class="server-item"><i class="fas fa-globe"></i><span>global server</span></div>
<div class="members-section">
<div class="section-header"><div class="section-title">Membros</div><div class="member-count" id="memberCount">0 membros</div></div>
<div id="membersList"></div>
</div>
</div>
<div class="main">
<div class="top-bar"><div class="channel-name">#chat-global</div></div>
<div class="chat-container" id="chatBox">
<div class="pinned-message">
Bem-vindo(a) ao NotBeBad! <br>
Evite spam e mensagens ofensivas.
</div>
</div>
<div class="input-area">
<input type="text" class="message-input" id="messageInput" placeholder="Mensagem..." onkeypress="handleEnter(event)"/>
<button class="send-btn" onclick="sendMessage()"><i class="fas fa-paper-plane"></i></button>
</div>
</div>

<div class="modal-overlay" id="profileModal">
<div class="profile-modal">
<div class="modal-title">Perfil</div>
<div class="pfp-large" id="modalPfp">Y</div>
<div class="status-badge" id="modalStatus"></div>
<div class="form-group"><label>Display Name</label><input type="text" id="displayName" readonly/></div>
<div class="form-group"><label>First Name</label><input type="text" id="firstName" readonly/></div>
<div class="btn-group"><button class="btn btn-close" onclick="closeModal()">Fechar</button><button class="btn btn-save" id="editBtn" onclick="toggleEdit()">Editar</button></div>
</div>
</div>

<script>
let socket;
let currentUser = "Você";
function connectWS() {
    socket = new WebSocket(`ws://${location.host}/ws`);
    socket.onmessage = e=>{
        const msg = JSON.parse(e.data);
        const chatBox = document.getElementById("chatBox");
        const div = document.createElement("div"); div.className="message";
        div.innerHTML=`<div class="pfp">${msg.username[0]}</div><div class="message-content">${msg.content}</div>`;
        chatBox.appendChild(div);
        chatBox.scrollTop=chatBox.scrollHeight;
    }
}

async function loadMembers() {
    const res = await fetch("/members"); const data = await res.json();
    const container=document.getElementById("membersList"); container.innerHTML="";
    data.forEach(m=>{
        const div=document.createElement("div"); div.className="member"; div.onclick=()=>{}; 
        div.innerHTML=`<div class="pfp">${m.displayName[0]}</div><div class="status-indicator ${m.status}"></div><div class="member-info">${m.displayName}</div>`;
        container.appendChild(div);
    });
    document.getElementById("memberCount").textContent=`${data.length} membros`;
}

function sendMessage() {
    const input=document.getElementById("messageInput"); const msg=input.value.trim(); if(!msg) return;
    socket.send(msg); input.value="";
}

function handleEnter(e){if(e.key==="Enter") sendMessage();}

window.onload=async()=>{
    await fetch("/login",{method:"POST"});
    connectWS();
    loadMembers();
    const msgs=await fetch("/messages").then(r=>r.json());
    const chatBox=document.getElementById("chatBox");
    msgs.forEach(m=>{const div=document.createElement("div");div.className="message";div.innerHTML=`<div class="pfp">${m.username[0]}</div><div class="message-content">${m.content}</div>`;chatBox.appendChild(div);});
};
</script>
</body>
</html>
"""

# ======================
# ROTAS
# ======================
async def index(request): return web.Response(text=HTML, content_type="text/html")

async def login(request):
    username = request.remote or "Você"
    cur.execute("INSERT OR IGNORE INTO users (username, display_name, first_name, status) VALUES (?,?,?,?)",
                (username, "Você", "User", "online"))
    conn.commit()
    return web.json_response({"ok": True})

async def members(request):
    cur.execute("SELECT username, display_name, first_name, status FROM users")
    users=[{"username":u[0],"displayName":u[1],"firstName":u[2],"status":u[3]} for u in cur.fetchall()]
    return web.json_response(users)

async def get_messages(request):
    cur.execute("SELECT username, content FROM messages")
    msgs=[{"username":u,"content":c} for u,c in cur.fetchall()]
    return web.json_response(msgs)

async def websocket_handler(request):
    ws=web.WebSocketResponse(); await ws.prepare(request)
    clients.add(ws)
    username=request.remote or "Você"
    async for msg in ws:
        if msg.type==web.WSMsgType.TEXT:
            cur.execute("INSERT INTO messages (username, content) VALUES (?,?)",(username,msg.data))
            conn.commit()
            data=json.dumps({"username":username,"content":msg.data})
            for client in clients:
                await client.send_str(data)
    clients.remove(ws)
    return ws

# ======================
# ADD ROTAS
# ======================
app.router.add_get("/", index)
app.router.add_post("/login", login)
app.router.add_get("/members", members)
app.router.add_get("/messages", get_messages)
app.router.add_get("/ws", websocket_handler)

# ======================
# RUN
# ======================
web.run_app(app, port=int(os.environ.get("PORT",8080)))

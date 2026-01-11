from aiohttp import web
import json

users = {}
sessions = {}
messages = []
friends = {}

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>NotBeBad</title>
<style>
body { margin:0; font-family:Arial; background:#2b2d31; color:white; }
#login, #chat { display:none; }
.sidebar { width:240px; background:#1e1f22; height:100vh; float:left; padding:10px; }
.chat { margin-left:240px; padding:10px; }
input, button { background:#383a40; color:white; border:none; padding:8px; margin:5px; }
.msg { margin:4px 0; }
.user { color:#8da1ff; }
</style>
</head>

<body>

<div id="login">
<h2>NotBeBad</h2>
<input id="username" placeholder="Nickname">
<input id="avatar" placeholder="Avatar URL">
<button onclick="login()">Entrar</button>
</div>

<div id="chat">
<div class="sidebar">
<h3>Perfil</h3>
<img id="avatarImg" width="80"><br>
<span id="me"></span>
<hr>
<h4>Sala Geral</h4>
</div>

<div class="chat">
<div id="messages"></div>
<input id="msg" placeholder="Mensagem">
<button onclick="send()">Enviar</button>
</div>
</div>

<script>
let ws;

function login(){
  fetch("/login",{
    method:"POST",
    body:JSON.stringify({
      user:username.value,
      avatar:avatar.value
    })
  }).then(r=>r.json()).then(d=>{
    document.getElementById("login").style.display="none";
    document.getElementById("chat").style.display="block";
    me.innerText = d.user;
    avatarImg.src = d.avatar;
    ws = new WebSocket("ws://"+location.host+"/ws");
    ws.onmessage = e=>{
      let m = JSON.parse(e.data);
      messages.innerHTML += `<div class="msg"><span class="user">${m.user}</span>: ${m.text}</div>`;
    }
  })
}

function send(){
  ws.send(msg.value);
  msg.value="";
}

document.getElementById("login").style.display="block";
</script>
</body>
</html>
"""

async def index(request):
    return web.Response(text=HTML, content_type="text/html")

async def login(request):
    data = await request.json()
    users[data["user"]] = data["avatar"]
    return web.json_response({"user":data["user"], "avatar":data["avatar"]})

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    user = list(users.keys())[-1]

    async for msg in ws:
        messages.append({"user":user,"text":msg.data})
        for client in request.app["sockets"]:
            await client.send_json({"user":user,"text":msg.data})

    return ws

app = web.Application()
app["sockets"] = []
app.router.add_get("/", index)
app.router.add_post("/login", login)
app.router.add_get("/ws", ws_handler)

web.run_app(app, port=8080)

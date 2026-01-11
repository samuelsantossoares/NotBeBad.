from aiohttp import web
import json
import os

# lista de usuários conectados
clients = []

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>NotBeBad Chat</title>
<style>
body { font-family: Arial; background:#1e1e1e; color:white; display:flex; justify-content:center; align-items:center; height:100vh; }
#app { width:400px; background:#2b2b2b; padding:10px; border-radius:10px; }
input, button { width:100%; margin:5px 0; padding:8px; border-radius:6px; border:none; background:#3b3b3b; color:white; }
#messages { height:300px; overflow:auto; border:1px solid #444; padding:5px; margin-bottom:5px; }
.msg { margin-bottom:6px; display:flex; align-items:center; }
.msg img { width:30px; height:30px; border-radius:50%; margin-right:6px; }
.msg span { font-weight:bold; margin-right:4px; }
</style>
</head>
<body>
<div id="app">
<div id="login">
<h3>NotBeBad Chat</h3>
<input id="nick" placeholder="Seu nick">
<input id="avatar" placeholder="URL da foto (opcional)">
<button onclick="joinChat()">Entrar</button>
</div>

<div id="chat" style="display:none;">
<div id="messages"></div>
<input id="msg" placeholder="Digite sua mensagem">
<button onclick="sendMessage()">Enviar</button>
</div>
</div>

<script>
let ws;
let user = {};

function joinChat(){
    let n = document.getElementById("nick").value.trim();
    if(!n) return alert("Coloque um nick!");
    user.nick = n;
    user.avatar = document.getElementById("avatar").value || "https://i.imgur.com/6VBx3io.png";
    ws = new WebSocket("ws://" + location.host + "/ws");

    ws.onopen = () => {
        ws.send(JSON.stringify({type:"join", user:user}));
        document.getElementById("login").style.display="none";
        document.getElementById("chat").style.display="block";
    };

    ws.onmessage = (e) => {
        let data = JSON.parse(e.data);
        if(data.type === "msg"){
            let m = document.createElement("div");
            m.className = "msg";
            m.innerHTML = `<img src="${data.avatar}"><span>${data.nick}:</span>${data.text}`;
            document.getElementById("messages").appendChild(m);
            document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
        }
    };
}

function sendMessage(){
    let input = document.getElementById("msg");
    if(input.value.trim()){
        ws.send(JSON.stringify({type:"msg", text:input.value}));
        input.value="";
    }
}
</script>
</body>
</html>
"""

@web.routes.get("/")
async def index(request):
    return web.Response(text=HTML, content_type="text/html")

@web.routes.get("/ws")
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    clients.append(ws)

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            data = json.loads(msg.data)
            if data["type"] == "join":
                ws.user = data["user"]
            elif data["type"] == "msg":
                user = getattr(ws, "user", {"nick":"Anon", "avatar":"https://i.imgur.com/6VBx3io.png"})
                for c in clients:
                    if not c.closed:
                        await c.send_str(json.dumps({
                            "type":"msg",
                            "nick": user["nick"],
                            "avatar": user["avatar"],
                            "text": data["text"]
                        }))
    clients.remove(ws)
    return ws

app = web.Application()
app.add_routes(web.routes)
port = int(os.environ.get("PORT", 8080))
web.run_app(app, port=port)

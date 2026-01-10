from aiohttp import web
import asyncio

routes = web.RouteTableDef()
clients = []

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>NotBeBad</title>
<style>
body {
    background:#0f0f0f;
    color:white;
    font-family:Arial;
    display:flex;
    justify-content:center;
    align-items:center;
    height:100vh;
}
#box {
    width:350px;
}
#chat {
    height:300px;
    border:1px solid #333;
    overflow:auto;
    padding:5px;
    margin-bottom:5px;
}
input, button {
    width:100%;
    padding:8px;
    margin-top:4px;
    background:#1e1e1e;
    color:white;
    border:none;
}
</style>
</head>
<body>
<div id="box">
    <h2>NotBeBad</h2>
    <div id="chat"></div>
    <input id="msg" placeholder="Digite algo">
    <button onclick="send()">Enviar</button>
</div>

<script>
let ws = new WebSocket("wss://" + location.host + "/ws");

ws.onmessage = (e) => {
    let chat = document.getElementById("chat");
    chat.innerHTML += "<div>" + e.data + "</div>";
    chat.scrollTop = chat.scrollHeight;
};

function send(){
    let i = document.getElementById("msg");
    ws.send(i.value);
    i.value = "";
}
</script>
</body>
</html>
"""

@routes.get("/")
async def index(request):
    return web.Response(text=HTML, content_type="text/html")

@routes.get("/ws")
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    clients.append(ws)

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            for c in clients:
                if not c.closed:
                    await c.send_str(msg.data)

    clients.remove(ws)
    return ws

app = web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app, port=8080)

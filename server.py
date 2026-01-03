import socketio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from game_logic import Game, Player

# 1. Setup Networking
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
async def redirect_to_game():
    return RedirectResponse(url="/static/index.html")

socket_app = socketio.ASGIApp(sio, app)

# 2. Game Instance
game = Game()

# 3. Socket Events
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    # Assign a default name like "Thief 1", "Thief 2"
    game.players[sid] = Player(sid, f"Thief {len(game.players) + 1}")
    await broadcast_state()

@sio.event
async def disconnect(sid):
    if sid in game.players:
        del game.players[sid]
    await broadcast_state()

@sio.event
async def change_name(sid, name):
    success, msg = game.change_player_name(sid, name)
    if success:
        await broadcast_state()
    else:
        # Send error only to the person trying to change the name
        await sio.emit('error', msg, room=sid)

@sio.event
async def start_game(sid):
    if game.start_game():
        await broadcast_state()

@sio.event
async def take_chip(sid, data):
    if game.handle_take_chip(sid, data['chip_value'], data['source']):
        await broadcast_state()

@sio.event
async def return_chip(sid):
    if game.handle_return_chip(sid):
        await broadcast_state()

@sio.event
async def toggle_settle(sid):
    if game.toggle_settle(sid):
        await broadcast_state()

async def broadcast_state():
    for pid in game.players:
        state = game.get_state(pid)
        await sio.emit('game_update', state, room=pid)

if __name__ == '__main__':
    import uvicorn
    print("Starting server on http://localhost:3000/static/index.html")
    uvicorn.run(socket_app, host='0.0.0.0', port=3000)
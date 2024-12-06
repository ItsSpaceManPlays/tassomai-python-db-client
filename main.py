import asyncio
import websockets
from websockets.server import ServerConnection
import sqlite3
import json
from typing import TypedDict

class ActionData(TypedDict):
    action: str
    data: str

IP = "localhost"
PORT = 45254

connections: dict[int, websockets.ServerProtocol] = {}

running = True

database_conn = sqlite3.connect('./answers.db')
database_cursor = database_conn.cursor()

def database_setup():
    database_cursor.execute("""
                            CREATE TABLE IF NOT EXISTS questions (
                                question TEXT NOT NULL,
                                answer TEXT NOT NULL
                            );
    """)

def get_question_answer(question: str) -> str:
    database_cursor.execute("SELECT answer FROM questions WHERE question = ?", (question,)) # this comma is very important dont remove it

    try:
        result = database_cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"[ERR ]: Failed to get answer: {e}")
        return None

def handle_disconnect(serverConn):
    client_ip, client_port, *_ = serverConn.remote_address
    print(f"[CONN]: {client_ip}:{client_port} disconnected")

    if client_port in connections:
        del connections[client_port]

async def conn(serverConn: websockets.ServerProtocol):
    client_ip, client_port, *_ = serverConn.remote_address
    print(f"[CONN]: {client_ip}:{client_port} connected")

    connections[client_port] = serverConn

    # await asyncio.sleep(1)

    await serverConn.send("<|ACK|>")
    while running:
        # await asyncio.sleep(1)
        # await serverConn.send("Hello")
        try:
            data = await serverConn.recv()
        except websockets.ConnectionClosed:
            handle_disconnect(serverConn)
            await serverConn.close()
            break

        print(f"[{client_ip}:{client_port}] [RECV]: {data}")
        if data == "close":
            handle_disconnect(serverConn)
            await serverConn.close()
            break

        try:
            j_data: ActionData = json.loads(data)
            if j_data["action"] == "qtoa":
                print(j_data)
                answer_to_question = get_question_answer(j_data["data"]) or "None"
                print(answer_to_question)
                await serverConn.send(answer_to_question)
        except:
            pass

async def main():
    print("[INIT]: Loading database")
    database_setup()
    print("[INIT]: Database loaded")

    print(f"[INIT]: Listening on {IP}:{PORT}")
    server = await websockets.serve(conn, IP, PORT)

    await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Closing")
        exit()
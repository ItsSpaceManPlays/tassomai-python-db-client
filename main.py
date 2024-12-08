import asyncio
import websockets
from websockets.server import ServerConnection
import sqlite3
import json
from typing import TypedDict
from errcodes import ERROR_CODES, ErrCode
import readchar
from tabulate import tabulate
from datetime import datetime

ADMIN_AUTH = "12345"

class ActionData(TypedDict):
    action: str
    data: str
    auth: str

IP = "localhost"
PORT = 45254

connections: dict[int, websockets.ServerProtocol] = {}

running = True
server = None

database_conn = sqlite3.connect('./answers.db')
database_cursor = database_conn.cursor()

start_time = datetime.now()
total_conns_ever = 0
total_disconns_ever = 0

async def input_loop():
    while True:
        usr_inp = await asyncio.to_thread(readchar.readchar)

        if usr_inp.lower() == "c":
            headers = ["ID", "Remote Address"]
            data = []
            for i, conn in enumerate(connections.values()):
                c_ip, c_port, *_ = conn.remote_address
                data.append([
                    i,
                    f"{c_ip}:{c_port}"
                ])

            data.append(["", f"Total Connections: {len(connections)}"])

            print(tabulate(
                data,
                headers=headers,
                tablefmt="simple_grid"
            ))

        elif usr_inp.lower() == "s":

            elapsed_time = (datetime.now() - start_time)
            seconds = int(elapsed_time.total_seconds())
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            print(f"Server uptime         : {hours:02}:{minutes:02}:{seconds:02}")
            print(f"Current connections   : {len(connections)}")
            print(f"Total connects ever   : {total_conns_ever}")
            print(f"Total disconnects ever: {total_disconns_ever}")

        elif usr_inp.lower() == "q":
            print("[QUIT ]: Shutting down server")

            global running
            running = False
            
            server.close()

            break

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
        print(f"[ERROR]: Failed to get answer: {e}")
        return None
    
def write_question_to_db(question: str, answer: str) -> ErrCode:
    try:
        database_cursor.execute("SELECT 1 FROM questions WHERE question = ?", (question,))
        if database_cursor.fetchone():
            return ERROR_CODES.DB_DUPEKEY;

        database_cursor.execute("INSERT INTO questions (question, answer) VALUES (?, ?)", (question, answer))
        database_conn.commit()
        return ERROR_CODES.DB_WRITESUCCESS;
    except:
        return ERROR_CODES.DB_WRITEEXCEPTION;

def handle_disconnect(serverConn):
    global total_disconns_ever
    total_disconns_ever += 1
    client_ip, client_port, *_ = serverConn.remote_address
    print(f"[CONN-]: {client_ip}:{client_port} disconnected; {len(connections) - 1} connections")

    if client_port in connections:
        del connections[client_port]

async def conn(serverConn: websockets.ServerProtocol):
    global total_conns_ever
    total_conns_ever += 1
    client_ip, client_port, *_ = serverConn.remote_address
    print(f"[CONN+]: {client_ip}:{client_port} connected; {len(connections) + 1} connections")

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

        if data == "keepalive":
            continue

        print(f"[RECV ]: [{client_ip}:{client_port}] {data}")
        if data == "close":
            handle_disconnect(serverConn)
            await serverConn.close()
            break

        try:
            j_data: ActionData = json.loads(data)
            print(f"[JSON ]: {j_data}")
            if j_data["action"] == "qtoa":
                answer_to_question = get_question_answer(j_data["data"]) or "None"
                print(answer_to_question)
                ret_string = json.dumps({
                    "code": 2,
                    "answer": answer_to_question
                })
                await serverConn.send(ret_string)
            if j_data["action"] == "wqdb":
                if j_data["auth"] == ADMIN_AUTH:
                    question, answer, *_ = j_data["data"].split("`~!")
                    print(f"[SAVE ]: Writing {question}:{answer} to answers.db")
                    err_code = write_question_to_db(question, answer)
                    ret_data = json.dumps({
                        "code": err_code.code,
                        "message": err_code.message
                    })
                    await serverConn.send(ret_data)
                else:
                    print(f"[AUTH ]: \'{j_data['auth']}\' is invalid")
                    await serverConn.send(json.dumps({
                        "code": 10
                    }))

        except Exception as e:
            print(f"[ERROR]: {e}")
            pass

async def main():
    global server

    print("[INIT ]: python websocket database hoster made by iTappedSpace, press q to exit")
    print("         c: connections")
    print("         s: statistics\n\n")

    print("[INIT ]: Loading database")
    database_setup()
    print("[INIT ]: Database loaded")

    print(f"[INIT ]: Listening on {IP}:{PORT}")
    server = await websockets.serve(
        conn,
        IP,
        PORT,
        ping_interval=None,
        ping_timeout=None,
        close_timeout=None
    )

    await asyncio.gather(server.wait_closed(), input_loop())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Closing")
        exit()
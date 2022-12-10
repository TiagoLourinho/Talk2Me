import sys
import socket
import json
import os
from datetime import datetime
import time
from threading import Thread, Lock

# Hyperparameters
PORT = 9999
LOGGING = False if os.getenv("TALK2ME_LOG") == "off" else True

# Macros
SUCCESS = "Success"
FAILURE = "Failure"

# Multithreading
shutdown = False
lock = Lock()


def register(conn: socket.socket, username: str, password: str) -> None:

    request = {"operation": "register", "username": username, "password": password}

    answer = send_request(conn, request)

    print(answer["info"])


def create_chat(
    conn: socket.socket, username: str, password: str, chat_name: str, users: list[str]
) -> None:

    request = {
        "operation": "createchat",
        "username": username,
        "password": password,
        "chatname": chat_name,
        "users": users,
    }

    answer = send_request(conn, request)

    print(answer["info"])


def chat_mode_send(conn: socket.socket, chat_name: str, token: str):
    global shutdown
    while not shutdown:
        message = input()

        if message.strip() == "exit":
            shutdown = True
            return

        request = {
            "operation": "sendmsg",
            "token": token,
            "chatname": chat_name,
            "msg": message,
        }

        with lock:
            answer = send_request(conn, request)

        if answer["rpl"] == FAILURE:
            print(answer["info"])
            shutdown = True


def chat_mode_recv(conn: socket.socket, chat_name: str, token: str):
    global shutdown
    while not shutdown:
        time.sleep(0.1)
        request = {"operation": "recvmsg", "token": token, "chatname": chat_name}
        with lock:
            answer = send_request(conn, request)

        if answer["rpl"] == SUCCESS:

            for message in answer["messages"]:
                print(f'{message["sender"]}: {message["msg"]}')
        else:
            print(answer["info"])
            shutdown = True


def chat(conn: socket.socket, username: str, password: str, chat_name: str) -> None:
    request = {"operation": "login", "username": username, "password": password}
    answer = send_request(conn, request)

    if answer["rpl"] == SUCCESS:
        token = answer["token"]

        print(f"Entering {chat_name}:")

        send_thread = Thread(target=chat_mode_send, args=(conn, chat_name, token))
        recv_thread = Thread(target=chat_mode_recv, args=(conn, chat_name, token))
        send_thread.start()
        recv_thread.start()

        send_thread.join()
        recv_thread.join()

    else:
        print(answer["info"])


def leave_chat(
    conn: socket.socket, username: str, password: str, chat_name: str
) -> None:
    request = {
        "operation": "leavechat",
        "username": username,
        "password": password,
        "chatname": chat_name,
    }

    answer = send_request(conn, request)

    print(answer["info"])


def list_users(conn: socket.socket) -> None:
    request = {"operation": "listusers"}

    answer = send_request(conn, request)

    if answer["rpl"] == SUCCESS:
        print("The current registed users are:")
        for user in answer["users"]:
            print(user)
    else:
        print(answer["info"])


def list_chats(conn: socket.socket) -> None:
    request = {"operation": "listchats"}

    answer = send_request(conn, request)

    if answer["rpl"] == SUCCESS:
        print("The current existent chats are:")
        for chat in answer["chats"]:
            print(chat)
    else:
        print(answer["info"])


def stats(conn: socket.socket) -> None:
    request = {"operation": "stats"}

    answer = send_request(conn, request)

    if answer["rpl"] == SUCCESS:
        print(
            f"Talk2Me currently has "
            f'{answer["stats"]["number_of_users"]} users, '
            f'{answer["stats"]["number_of_chats"]} chats, '
            f'{answer["stats"]["number_of_sent_messages"]} '
            f"sent messages and average operatioon TO DO"
        )

    else:
        print(answer["info"])


def wait_for_answer(conn: socket.socket) -> str:
    # Receive message
    data = ""
    while True:
        data += conn.recv(4096).decode("utf-8")

        # Message is complete
        if "}\r\n" in data:
            data = data.strip()

            if LOGGING:
                now = str(datetime.now())
                now = now[: now.index(".")]
                print(f"[{now}]: {data}")

            return data


def send_request(conn: socket.socket, request: object) -> None:

    request = json.dumps(request)

    if LOGGING:
        now = str(datetime.now())
        now = now[: now.index(".")]
        print(f"[{now}]: {request}")

    conn.sendall(bytes(request + "\r\n", "utf-8"))

    answer = wait_for_answer(conn)

    answer = json.loads(answer)

    return answer


def main() -> None:
    host = sys.argv[1]
    operation = sys.argv[2]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
        conn.connect((host, PORT))

        match operation:
            case "register":
                register(conn, sys.argv[3], sys.argv[4])
            case "createchat":
                create_chat(
                    conn,
                    sys.argv[3],
                    sys.argv[4],
                    sys.argv[5],
                    [sys.argv[i] for i in range(6, len(sys.argv))],
                )
            case "chat":
                chat(conn, sys.argv[3], sys.argv[4], sys.argv[5])
            case "leavechat":
                leave_chat(conn, sys.argv[3], sys.argv[4], sys.argv[5])
            case "listusers":
                list_users(conn)
            case "listchats":
                list_chats(conn)
            case "stats":
                stats(conn)


if __name__ == "__main__":
    main()

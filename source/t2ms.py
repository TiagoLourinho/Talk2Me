import socket
from threading import Thread
import json
import os
from datetime import datetime

from adts import Database

# Hyperparameters
HOST = ""
PORT = 9999
LOGGING = False if os.getenv("TALK2ME_LOG") == "off" else True
MAX_THREADS = 5  # Number of threads
SOCKET_TIMEOUT = 1  # seconds

# Macros
SUCCESS = "Success"
FAILURE = "Failure"

# Multithreading
active_threads = set()

# Database
database = Database()
active_sockets = dict()


def register(username: str, password: str) -> tuple[str]:

    # Check if user already exists
    if database.exists_user(username):
        return FAILURE, "Username already in use"

    database.create_user(username, password)

    return SUCCESS, "User registered successfully"


def login(username: str, password: str) -> tuple[str]:

    # Check if user exists
    if not database.exists_user(username):
        return FAILURE, "User isn't registered"

    # Check if password is correct
    if not database.is_password_correct(username, password):
        return FAILURE, "Password is incorrect"

    return database.open_user_session(username), "Login was successfully"


def create_chat(
    username: str, password: str, chat_name: str, users: list[str]
) -> tuple[str]:
    token, message = login(username, password)

    # Error in login
    if token == FAILURE:
        return token, message

    # Chat already exists
    if database.exists_chat(chat_name):
        return FAILURE, "A chat with the same name already exist"

    # Check if all the users are registered
    for user in users:
        if not database.exists_user(user):
            return FAILURE, "{user} is not registered"

    database.create_chat(username)

    database.add_user_to_chat(username, chat_name)
    for user in users:
        database.add_user_to_chat(user, chat_name)

    database.close_user_session(token)

    return SUCCESS, "Created the chat successfully"


def send_msg(user_token: str, chat_name: str, msg: str) -> tuple[str]:

    # Check if user has done login
    if not database.is_user_logged_in(user_token):
        return FAILURE, "User was not logged in"

    # Check if chat exist
    if not database.exists_chat(chat_name):
        return FAILURE, "Chat doesn't exist"

    # Check if user in in the chat
    if not database.is_user_in_chat(user_token, chat_name, use_token_instead=True):
        return FAILURE, "User is not in the chat"

    database.send_message(user_token, chat_name, msg)

    return SUCCESS, "Message sent"


def recv_msg(user_token: str, chat_name: str) -> list[dict[str:str]] | tuple[str]:

    # Check if user has done login
    if not database.is_user_logged_in(user_token):
        return FAILURE, "User was not logged in"

    # Check if chat exist
    if not database.exists_chat(chat_name):
        return FAILURE, "Chat doesn't exist"

    # Check if user in in the chat
    if not database.is_user_in_chat(user_token, chat_name, use_token_instead=True):
        return FAILURE, "User is not in the chat"

    return database.get_unseen_messages(user_token, chat_name), "Messages received"


def leave_chat(username: str, password: str, chat_name: str) -> tuple[str]:
    token, message = login(username, password)

    # Error in login
    if token == FAILURE:
        return token, message

    # Check if chat exist
    if not database.exists_chat(chat_name):
        return FAILURE, "Chat doesn't exist"

    # Check if user in in the chat
    if not database.is_user_in_chat(username, chat_name):
        return FAILURE, "User is not in the chat"

    database.remove_user_from_chat(username, chat_name)

    database.close_user_session(token)

    return SUCCESS, "User removed successfully"


def list_users() -> tuple[list[str], str]:
    return database.list_users(), "List of users sent"


def list_chats() -> tuple[list[str], str]:
    return database.list_chats(), "List of chats sent"


def stats() -> tuple[dict[str : int | float], str]:
    return database.get_stats(), "Stats sent"


def handle_request(conn: socket) -> None:
    data = ""

    with conn:

        # Receive full message
        while True:
            received = conn.recv(1024).decode("utf-8")

            if received:
                data += received
            else:
                break

        if LOGGING:
            t = str(datetime.now())[: t.index(".")]
            print(f"[{t}]: {data}")

        data = json.loads(data)

        match data["operation"]:
            case "register":
                rpl, info = register(data["username"], data["password"])

                answer = {"rpl": rpl, "info": info}

            case "createchat":
                rpl, info = create_chat(
                    data["username"],
                    data["password"],
                    data["chatname"],
                    data["users"],
                )

                answer = {"rpl": rpl, "info": info}

            case "login":
                token, info = login(data["username"], data["password"])

                if token != FAILURE:
                    answer = {"rpl": SUCCESS, "info": info, "token": token}
                else:
                    answer = {"rpl": FAILURE, "info": info}

            case "sendmsg":
                rpl, info = send_msg(data["token"], data["chatname"], data["message"])

                answer = {"rpl": rpl, "info": info}

            case "recvmsg":
                messages, info = recv_msg(data["token"], data["chatname"])

                if messages != FAILURE:
                    answer = {"rpl": SUCCESS, "info": info, "messages": messages}
                else:
                    answer = {"rpl": FAILURE, "info": info}

            case "leavechat":
                rpl, info = leave_chat(
                    data["username"], data["password"], data["chatname"]
                )
                answer = {"rpl": rpl, "info": info}

            case "listusers":
                users, info = list_users()

                if users != FAILURE:
                    answer = {"rpl": SUCCESS, "info": info, "users": users}
                else:
                    answer = {"rpl": FAILURE, "info": info}

            case "listchats":
                chats, info = list_chats()

                if chats != FAILURE:
                    answer = {"rpl": SUCCESS, "info": info, "chats": chats}
                else:
                    answer = {"rpl": FAILURE, "info": info}

            case "stats":
                s, info = stats()

                if s != FAILURE:
                    answer = {"rpl": SUCCESS, "info": info, "stats": s}
                else:
                    answer = {"rpl": FAILURE, "info": info}

            case default:
                answer = {"rpl": FAILURE, "info": "Invalid request"}

        answer = json.dumps(answer)

        if LOGGING:
            t = str(datetime.now())[: t.index(".")]
            print(f"[{t}]: {answer}")

        conn.sendall(answer)


def main() -> None:

    socket.setdefaulttimeout(SOCKET_TIMEOUT)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(MAX_THREADS)

        while True:
            try:
                conn, _ = s.accept()
            except TimeoutError:

                # Clean up dead threads
                if len(active_threads) > MAX_THREADS:
                    for t in active_threads.copy():
                        if not t.is_alive():
                            t.join()
                            active_threads.remove(t)

                continue

            # Handle client request
            t = Thread(target=handle_request, args=(conn,))
            active_threads.add(t)
            t.start()


if __name__ == "__main__":
    main()

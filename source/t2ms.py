import socket
from threading import Thread
import json
import os
from datetime import datetime

from adts import Database

# Hyperparameters
HOST = ""
PORT = 9999
LOGGING = True if os.getenv("TALK2ME_LOG") == "on" else False
MAX_THREADS = 5  # Number of threads
SOCKET_TIMEOUT = 0.5  # seconds

# Macros
SUCCESS = "Success"
FAILURE = "Failure"

# Multithreading
active_threads = set()

# Database
database = Database()


############################## Requests ##############################


def register(username: str, password: str) -> tuple[str]:
    """Regists an user in the database"""

    # Check if user already exists
    if database.exists_user(username):
        return FAILURE, "Username already in use"

    database.create_user(username, password)

    return SUCCESS, "User registered successfully"


def login(username: str, password: str, chat_name: str = None) -> tuple[str]:
    """Opens an user session"""

    # Check if user exists
    if not database.exists_user(username):
        return FAILURE, "User isn't registered"

    # Check if password is correct
    if not database.is_password_correct(username, password):
        return FAILURE, "Password is incorrect"

    # In the case where the login was made to enter chat mode
    if chat_name is not None:
        if not database.is_user_in_chat(username, chat_name):
            return FAILURE, "User is not in this chat"

    return database.open_user_session(username), "Login was successfully"


def create_chat(
    username: str, password: str, chat_name: str, users: list[str]
) -> tuple[str]:
    """Creates a chat"""

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

    database.create_chat(chat_name)

    database.add_user_to_chat(username, chat_name)
    for user in users:
        database.add_user_to_chat(user, chat_name)

    database.close_user_session(token)

    return SUCCESS, "Created the chat successfully"


def send_msg(user_token: str, chat_name: str, msg: str) -> tuple[str]:
    """Sends a message to a chat"""

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
    """Returns unseen messages"""

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
    """Leaves a chat"""

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
    """List the current users"""

    return database.get_list_users(), "List of users sent"


def list_chats() -> tuple[list[str], str]:
    """List the current chats"""

    return database.get_list_chats(), "List of chats sent"


def stats() -> tuple[dict[str : int | float], str]:
    """List some stats about Talk2Me"""

    return database.get_stats(), "Stats sent"


############################## Client interaction ##############################


def send_answer(conn: socket.socket, answer: object) -> None:
    """Sends an answer to the client"""

    answer = json.dumps(answer)

    log(answer, sent=True)

    conn.sendall(bytes(answer + "\r\n", "utf-8"))


def receive_request(conn: socket.socket) -> object | bool:
    """Receives a request from the client"""

    request = ""
    while True:
        request += conn.recv(4096).decode("utf-8")

        # Connection was closed
        if not request:
            return False

        # Check if message is complete
        if "\r\n" in request:
            request = request.strip()

            log(request, sent=False)

            return json.loads(request)


############################## Thread methods ##############################


def handle_request(conn: socket.socket) -> None:

    token = None

    with conn:

        while True:

            request = receive_request(conn)

            # Connection closed
            if not request:
                break

            match request["operation"]:
                case "register":
                    rpl, info = register(request["username"], request["password"])

                    answer = {"rpl": rpl, "info": info}

                case "createchat":
                    rpl, info = create_chat(
                        request["username"],
                        request["password"],
                        request["chatname"],
                        request["users"],
                    )

                    answer = {"rpl": rpl, "info": info}

                case "login":
                    token, info = login(
                        request["username"],
                        request["password"],
                        request.get("chatname"),
                    )

                    if token != FAILURE:
                        answer = {"rpl": SUCCESS, "info": info, "token": token}
                    else:
                        answer = {"rpl": FAILURE, "info": info}

                case "sendmsg":
                    rpl, info = send_msg(
                        request["token"], request["chatname"], request["msg"]
                    )

                    answer = {"rpl": rpl, "info": info}

                case "recvmsg":
                    messages, info = recv_msg(request["token"], request["chatname"])

                    if messages != FAILURE:
                        answer = {
                            "rpl": SUCCESS,
                            "info": info,
                            "messages": messages,
                        }
                    else:
                        answer = {"rpl": FAILURE, "info": info}

                case "leavechat":
                    rpl, info = leave_chat(
                        request["username"], request["password"], request["chatname"]
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

                case _:
                    answer = {"rpl": FAILURE, "info": "Invalid request"}

            send_answer(conn, answer)

    # Close user session
    if token is not None:
        database.close_user_session(token)


############################## Utilities ##############################


def log(string: str, sent: bool) -> None:
    """Logs the request receibev or the answer sent"""

    CYAN = "\033[96m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

    if LOGGING:
        now = datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M:%S")

        format = CYAN if sent else BLUE

        print(format + f"[{now}]: {string}" + RESET)


def clean_up_threads():
    """Checks for finished threads and cleans them"""

    for t in active_threads.copy():
        if not t.is_alive():
            t.join()
            active_threads.remove(t)


############################## Main ##############################


def main() -> None:

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(SOCKET_TIMEOUT)
        s.bind((HOST, PORT))
        s.listen()

        while True:
            try:
                conn, _ = s.accept()
            except TimeoutError:
                clean_up_threads()
                continue

            # Handle client request
            t = Thread(target=handle_request, args=(conn,))
            active_threads.add(t)
            t.start()

            if len(active_threads) > MAX_THREADS:
                clean_up_threads()


if __name__ == "__main__":
    main()

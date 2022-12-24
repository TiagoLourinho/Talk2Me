import socket
from threading import Thread
import json
from datetime import datetime
from cryptography.fernet import Fernet
from time import time

from adts import Database
from config import *

############################## Thread methods ##############################


def handle_request(conn: socket.socket) -> None:

    token = None

    with conn:

        while True:

            request = receive_message(conn)
            start = time()

            # Connection closed
            if not request:
                break

            # Request comes from main server
            if request.get("server_operation") is not None:
                match request["server_operation"]:
                    case "createchat":
                        create_chat_in_chat_server(
                            request["chatname"], request["users"]
                        )
                    case "leavechat":
                        leave_chat_in_chat_server(
                            request["chatname"], request["username"]
                        )
                    case "stats":
                        rpl, feedback, s = get_stats_in_chat_server()

                        if rpl == SUCCESS:
                            answer = {"rpl": SUCCESS, "feedback": feedback, "stats": s}
                        else:
                            answer = {"rpl": FAILURE, "feedback": feedback}

                        send_message(conn, answer)
            # Request comes from a client
            else:
                match request["operation"]:
                    case "register":
                        rpl, feedback = register(
                            request["username"], request["password"]
                        )

                        answer = {"rpl": rpl, "feedback": feedback}

                    case "createchat":
                        rpl, feedback = create_chat(
                            request["username"],
                            request["password"],
                            request["chatname"],
                            request["users"],
                        )

                        answer = {"rpl": rpl, "feedback": feedback}

                    case "login":
                        rpl, feedback, token, extra_info = login(
                            request["username"],
                            request["password"],
                            request.get("chatname"),
                        )

                        if rpl == SUCCESS:
                            answer = {
                                "rpl": SUCCESS,
                                "feedback": feedback,
                                "token": token,
                            }
                        else:
                            answer = {"rpl": FAILURE, "feedback": feedback}

                        if extra_info is not None:
                            # Support for chat mode and sends the messages right away
                            if type(extra_info) is list:
                                answer["messages"] = extra_info
                            # Redirect client to other server
                            elif type(extra_info) is str:
                                answer["redirect"] = extra_info

                    case "sendmsg":
                        rpl, feedback = send_msg(
                            request["token"], request["chatname"], request["msg"]
                        )

                        answer = {"rpl": rpl, "feedback": feedback}

                    case "recvmsg":
                        rpl, feedback, messages = recv_msg(
                            request["token"], request["chatname"]
                        )

                        if rpl == SUCCESS:
                            answer = {
                                "rpl": SUCCESS,
                                "feedback": feedback,
                                "messages": messages,
                            }
                        else:
                            answer = {"rpl": FAILURE, "feedback": feedback}

                    case "leavechat":
                        rpl, feedback = leave_chat(
                            request["username"],
                            request["password"],
                            request["chatname"],
                        )
                        answer = {"rpl": rpl, "feedback": feedback}

                    case "listusers":
                        rpl, feedback, users = list_users()

                        if rpl == SUCCESS:
                            answer = {
                                "rpl": SUCCESS,
                                "feedback": feedback,
                                "users": users,
                            }
                        else:
                            answer = {"rpl": FAILURE, "feedback": feedback}

                    case "listchats":
                        rpl, feedback, chats = list_chats()

                        if rpl == SUCCESS:
                            answer = {
                                "rpl": SUCCESS,
                                "feedback": feedback,
                                "chats": chats,
                            }
                        else:
                            answer = {"rpl": FAILURE, "feedback": feedback}

                    case "stats":
                        rpl, feedback, s = stats()

                        if rpl == SUCCESS:
                            answer = {"rpl": SUCCESS, "feedback": feedback, "stats": s}
                        else:
                            answer = {"rpl": FAILURE, "feedback": feedback}

                    case _:
                        answer = {"rpl": FAILURE, "feedback": "Invalid request"}

                send_message(conn, answer)
                end = time()

                database.update_average_operation_latency(end - start)

            database.backup()

    # Close user session
    if token is not None:
        database.close_user_session(token)

    database.backup()


############################## Requests ##############################


def register(username: str, password: str) -> tuple[str]:
    """Regists an user in the database"""

    # Check if user already exists
    if database.exists_user(username):
        return FAILURE, "Username already in use"

    database.create_user(username, password)

    return SUCCESS, "User registered successfully"


def login(
    username: str, password: str, chat_name: str = None
) -> tuple[str | list[dict[str:str]]]:
    """Opens an user session"""

    # Redirect client
    if chat_name is not None:
        server = database.get_associated_server(chat_name)
        if server is not None:
            return FAILURE, "Redirect client", None, server

    # Check if user exists
    if not database.exists_user(username):
        return FAILURE, "User isn't registered", None, None

    # Check if password is correct
    if not database.is_password_correct(username, password):
        return FAILURE, "Password is incorrect", None, None

    # In the case where the login was made to enter chat mode
    if chat_name is not None:

        # Chat doesn't already exists
        if not database.exists_chat(chat_name):
            return FAILURE, "The chat doesn't exist", None, None

        # Check if user in in the chat
        if not database.is_user_in_chat(username, chat_name):
            return FAILURE, "User is not in this chat", None, None

        token = database.open_user_session(username)

        # Clear unseen messages because all messages will be returned
        database.get_unseen_messages(token, chat_name)

        return (
            SUCCESS,
            "Login was successfully",
            token,
            database.get_chat_messages(chat_name),
        )
    else:
        return (
            SUCCESS,
            "Login was successfully",
            database.open_user_session(username),
            None,
        )


def create_chat(
    username: str, password: str, chat_name: str, users: list[str]
) -> tuple[str]:
    """Creates a chat"""

    rpl, message, token, _ = login(username, password)

    # Error in login
    if rpl == FAILURE:
        return FAILURE, message

    # Chat already exists
    if database.exists_chat(chat_name):
        database.close_user_session(token)
        return FAILURE, "A chat with the same name already exist"

    # Check if all the users are registered
    for user in users:
        if not database.exists_user(user):
            database.close_user_session(token)
            return FAILURE, f"{user} is not registered"

    # Create the chat and add the users
    database.create_chat(chat_name)

    database.add_user_to_chat(username, chat_name)
    for user in users:
        database.add_user_to_chat(user, chat_name)

    # Inform the chat server of the newly created chat
    server = database.get_lowest_load_server()

    if server is not None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            try:
                conn.connect((server, PORT))
                info = {
                    "server_operation": "createchat",
                    "chatname": chat_name,
                    "users": [
                        {"username": user, "password": database.get_user_password(user)}
                        for user in (users + [username])
                    ],
                }

                send_message(conn, info)

                database.associate_chat_with_server(chat_name, server)

            except ConnectionRefusedError:
                pass

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
        return FAILURE, "User was not logged in", None

    # Check if chat exist
    if not database.exists_chat(chat_name):
        return FAILURE, "Chat doesn't exist", None

    # Check if user in in the chat
    if not database.is_user_in_chat(user_token, chat_name, use_token_instead=True):
        return FAILURE, "User is not in the chat", None

    return (
        SUCCESS,
        "Messages received",
        database.get_unseen_messages(user_token, chat_name),
    )


def leave_chat(username: str, password: str, chat_name: str) -> tuple[str]:
    """Leaves a chat"""

    rpl, message, token, _ = login(username, password)

    # Error in login
    if rpl == FAILURE:
        return FAILURE, message

    # Check if chat exist
    if not database.exists_chat(chat_name):
        database.close_user_session(token)
        return FAILURE, "Chat doesn't exist"

    # Check if user in in the chat
    if not database.is_user_in_chat(username, chat_name):
        database.close_user_session(token)
        return FAILURE, "User is not in the chat"

    # Remove user
    database.remove_user_from_chat(username, chat_name)

    # Inform the chat server of the newly created chat
    server = database.get_associated_server(chat_name)

    if server is not None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            try:
                conn.connect((server, PORT))
                info = {
                    "server_operation": "leavechat",
                    "chatname": chat_name,
                    "username": username,
                }

                send_message(conn, info)

            except ConnectionRefusedError:
                pass

    database.close_user_session(token)

    return SUCCESS, "User removed successfully"


def list_users() -> tuple[list[str], str]:
    """List the current users"""

    return SUCCESS, "List of users sent", database.get_list_users()


def list_chats() -> tuple[list[str], str]:
    """List the current chats"""

    return SUCCESS, "List of chats sent", database.get_list_chats()


def stats() -> tuple[dict[str : int | float], str]:
    """List some stats about Talk2Me"""

    # Main stats
    stats = database.get_stats()

    # Get number of messages sent in the chat servers
    for server in CHAT_SERVERS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            try:
                conn.connect((server, PORT))
                request = {"server_operation": "stats"}

                send_message(conn, request)

                chat_stats = receive_message(conn)

                # Connection was closed
                if not chat_stats:
                    continue

                # The only thing that the main server doesn't know is the number of messages
                stats["number_of_sent_messages"] += chat_stats["stats"][
                    "number_of_sent_messages"
                ]

            except ConnectionRefusedError:
                continue

    return SUCCESS, "Stats sent", stats


############################## Chat server ##############################


def create_chat_in_chat_server(chat_name: str, users: list[dict[str:str]]) -> None:
    """Creates the chat and users in the chat server"""

    database.create_chat(chat_name)

    for user in users:

        # User might be already in another chat of this chat server
        if not database.exists_user(user["username"]):
            database.create_user(
                user["username"], user["password"], already_encrypted=True
            )

        database.add_user_to_chat(user["username"], chat_name)


def leave_chat_in_chat_server(chat_name: str, username: str) -> None:
    """Removes a user from a chat in the chat server"""

    database.remove_user_from_chat(username, chat_name)


def get_stats_in_chat_server() -> tuple[dict[str : int | float], str]:
    """Returns the stats in the chat server"""

    return SUCCESS, "Stats sent", database.get_stats()


############################## Client interaction ##############################


def send_message(conn: socket.socket, message: object) -> None:
    """Sends an answer to the client or a request to chat server"""

    message = json.dumps(message)

    log(message, sent=True)

    message = fernet.encrypt(message.encode()).decode()

    conn.sendall((message + "\r\n").encode())


def receive_message(conn: socket.socket) -> object | bool:
    """Receives a request from the client or a message from chat server"""

    message = ""
    while True:
        message += conn.recv(4096).decode()

        # Connection was closed
        if not message:
            return False

        # Check if message is complete
        if "\r\n" in message:
            message = message.strip()

            message = fernet.decrypt(message.encode()).decode()

            log(message, sent=False)

            return json.loads(message)


############################## Utilities ##############################


def log(string: str, sent: bool) -> None:
    """Logs the request receibev or the answer sent"""

    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"

    if LOGGING:
        now = datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M:%S")

        format = CYAN if sent else BLUE

        print(format + f'[{now}][{"SENT" if sent else "RECEIVED"}]: {string}' + RESET)


def clean_up_threads(active_threads: set[Thread]) -> None:
    """Checks for finished threads and cleans them"""

    for t in active_threads.copy():
        if not t.is_alive():
            t.join()
            active_threads.remove(t)


############################## Main ##############################


def main() -> None:
    print("* Talk2Me server is now running ")
    print(f'* Logging: {"on" if LOGGING else "off"}')

    active_threads = set()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(SOCKET_TIMEOUT)
        s.bind(("", PORT))
        s.listen()

        while True:
            try:
                conn, _ = s.accept()
            except TimeoutError:
                clean_up_threads(active_threads)
                continue

            # Handle client request
            t = Thread(target=handle_request, args=(conn,))
            active_threads.add(t)
            t.start()

            if len(active_threads) > MAX_THREADS:
                clean_up_threads(active_threads)


if __name__ == "__main__":

    database = Database(CHAT_SERVERS)
    fernet = Fernet(ENCRYPTION_KEY)

    main()

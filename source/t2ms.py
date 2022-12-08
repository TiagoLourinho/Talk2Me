import socket
from threading import Thread, Lock
import json
import os
from datetime import datetime

from adts import User, Message, Chat

threads = list()

users = dict()
chats = dict()
session_tokens = set()

lock = Lock()

HOST = ""
PORT = 9999
LOGGING = False if os.getenv("TALK2ME_LOG") == "off" else True


def register(username: str, password: str) -> bool:

    with lock:
        if username not in users:
            users[username] = User(username, password)
            return True
        else:
            return False


def login(username: str, password: str) -> str | bool:

    with lock:
        # Check if user is registered
        if username not in users:
            return False

        # Check if password is correct
        if not users[username].is_password_correct(password):
            return False

        token = user_to_token(users[username])
        session_tokens.add(token)

        return token


def create_chat(username: str, password: str, chat_name: str, users: list[str]) -> bool:
    token = login(username, password)

    # Error in login
    if not token:
        return False

    with lock:

        # Chat already exists
        if chat_name in chats:
            return False

        chat = Chat(chat_name)

        chat.add_user(users[username])

        for user in users:

            # Check if users are registered
            if user not in users:
                return False
            else:
                chat.add_user(users[user])

        chats[chat_name] = chat

        session_tokens.remove(token)
        return True


def send_msg(user_token: str, chat_name: str, msg: str) -> bool:
    with lock:

        # Check if user has done login
        if user_token not in session_tokens:
            return False

        # Chat doesn't exist
        if chat_name not in chats:
            return False

        chats[chat_name].send_message(Message(token_to_user(user_token), msg))

        return True


def recv_msg(user_token: str, chat_name: str) -> list[dict[str:str]] | bool:
    with lock:
        # Check if user has done login
        if user_token not in session_tokens:
            return False

        # Chat doesn't exist
        if chat_name not in chats:
            return False

        messages = chats[chat_name].get_unseen_messages(token_to_user(user_to_token))

        return [
            {"sender": msg.get_sender(), "message": msg.get_message()}
            for msg in messages
        ]


def leave_chat(username: str, password: str, chat_name: str) -> bool:
    token = login(username, password)

    # Error in login
    if not token:
        return False

    with lock:
        # Chat doesn't exist
        if chat_name not in chats:
            return False

        # User was not in the cat
        if users[username] not in chats[chat_name]:
            return False

        chats[chat_name].remove_user(users[username])

        session_tokens.remove(token)
        return True


def list_users() -> list[str]:
    with lock:
        return list(users.keys())


def list_chats() -> list[str]:
    with lock:
        return list(chats.keys())


def stats() -> dict[str : int | float]:
    with lock:
        return {
            "number_of_users": len(users),
            "number_of_chats": len(chats),
            "number_of_sent_messages": sum([len(chat) for chat in chats]),
        }


def user_to_token(user: User) -> str:
    return user.get_username()


def token_to_user(token: str) -> User:
    return users[token]


def handle_request(conn: socket) -> None:
    data = ""
    SUCCESS = "Success"
    FAILURE = "Failure"

    # Receive full message
    with conn:
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
                answer = {
                    "rpl": SUCCESS
                    if register(data["username"], data["password"])
                    else FAILURE
                }

            case "createchat":
                answer = {
                    "rpl": SUCCESS
                    if create_chat(
                        data["username"],
                        data["password"],
                        data["chatname"],
                        data["users"],
                    )
                    else FAILURE
                }

            case "sendmsg":
                answer = {
                    "rpl": SUCCESS
                    if send_msg(data["token"], data["chatname"], data["message"])
                    else FAILURE
                }

            case "recvmsg":
                messages = recv_msg(data["token"], data["chatname"])
                answer = {"rpl": SUCCESS if messages else FAILURE}
                if messages:
                    answer["messages"] = messages

            case "leavechat":
                answer = {
                    "rpl": SUCCESS
                    if leave_chat(data["username"], data["password"], data["chatname"])
                    else FAILURE
                }

            case "listusers":
                users = list_users()
                answer = {"rpl": SUCCESS if users else FAILURE}
                if users:
                    answer["users"] = users

            case "listchats":
                chats = list_chats()
                answer = {"rpl": SUCCESS if chats else FAILURE}
                if chats:
                    answer["chats"] = chats

            case "stats":
                s = stats()
                answer = {"rpl": SUCCESS if s else FAILURE}
                if s:
                    answer["stats"] = s

            case default:
                answer = {"rpl": FAILURE}

        answer = json.dumps(answer)

        if LOGGING:
            t = str(datetime.now())[: t.index(".")]
            print(f"[{t}]: {answer}")

        conn.sendall(answer)


def clean_threads() -> None:
    for t in threads:
        if not t.is_alive():
            t.join()


def main() -> None:

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(5)

        while True:
            conn, _ = s.accept()

            # Handle clien request
            threads.append(Thread(target=handle_request, args=(conn,)))
            threads[-1].start()

            # Clean up threads
            threads.append(Thread(target=clean_threads))
            threads[-1].start()


if __name__ == "__main__":
    main()

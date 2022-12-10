import hashlib
import secrets
import threading

from adts import User, Message, Chat


class Database:
    def __init__(self) -> None:
        self.__users: dict[str, User] = dict()
        self.__tokens: dict[str, User] = dict()
        self.__chats: dict[str, Chat] = dict()
        self.__lock = threading.Lock()

    ##### User management #####

    def exists_user(self, username: str) -> bool:
        with self.__lock:
            return username in self.__users

    def create_user(self, username: str, password: str) -> None:
        with self.__lock:
            self.__users[username] = User(username, self.encode_password(password))

    def is_password_correct(self, username: str, password: str) -> bool:
        with self.__lock:
            return self.__users[username].is_password_correct(
                self.encode_password(password)
            )

    def open_user_session(self, username: str) -> str:
        with self.__lock:
            token = self.generate_token()
            self.__tokens[token] = self.__users[username]
            return token

    def close_user_session(self, user_token: str) -> None:
        with self.__lock:
            self.__tokens.pop(user_token)

    def is_user_logged_in(self, user_token: str) -> bool:
        with self.__lock:
            return user_token in self.__tokens

    ##### Chat management #####

    def exists_chat(self, chat_name: str) -> bool:
        with self.__lock:
            return chat_name in self.__chats

    def create_chat(self, chat_name: str) -> None:
        with self.__lock:
            self.__chats[chat_name] = Chat(chat_name)

    def add_user_to_chat(self, username: str, chat_name: str) -> None:
        with self.__lock:
            self.__chats[chat_name].add_user(self.__users[username])

    def is_user_in_chat(
        self, user: str, chat_name: str, use_token_instead: bool = False
    ) -> bool:
        with self.__lock:
            if not use_token_instead:
                return self.__users[user] in self.__chats[chat_name]
            else:
                return self.__tokens[user] in self.__chats[chat_name]

    def send_message(self, user_token: str, chat_name: str, msg: str) -> None:
        with self.__lock:
            self.__chats[chat_name].send_message(
                Message(self.__tokens[user_token], msg)
            )

    def get_unseen_messages(
        self, user_token: str, chat_name: str
    ) -> list[dict[str:str]]:
        with self.__lock:
            return [
                {
                    "sender": msg.get_sender().get_username(),
                    "msg": msg.get_message(),
                    "time": msg.get_time().strftime("%Y-%m-%d %H:%M:%S"),
                }
                for msg in self.__chats[chat_name].get_unseen_messages(
                    self.__tokens[user_token]
                )
            ]

    def remove_user_from_chat(self, username: str, chat_name: str) -> None:
        with self.__lock:
            self.__chats[chat_name].remove_user(self.__users[username])

    ##### Utils #####
    def list_users(self) -> list[str]:
        with self.__lock:
            return list(self.__users.keys())

    def list_chats(self) -> list[str]:
        with self.__lock:
            return list(self.__chats.keys())

    def get_stats(self) -> dict[str : int | float]:
        with self.__lock:
            return {
                "number_of_users": len(self.__users),
                "number_of_chats": len(self.__chats),
                "number_of_sent_messages": sum(
                    [len(chat) for chat in self.__chats.values()]
                ),
                "average_operation_latency": 0,
            }

    def encode_password(self, password: str) -> str:
        return hashlib.sha256(bytes(password, "utf-8")).hexdigest()

    def generate_token(self) -> str:
        return secrets.token_hex(32)

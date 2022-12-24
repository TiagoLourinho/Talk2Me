import hashlib
import secrets
import threading
import pickle
import os
import sys

from adts import User, Message, Chat


class Database:
    """Class representing a thread safe database of Talk2Me"""

    def __init__(self, chat_servers: list[str]) -> None:

        backup = None

        # Check if there is a backup available to load from
        if os.path.exists("backup.pickle"):

            with open("backup.pickle", "rb") as f:
                backup = pickle.load(f)

        self.__users: dict[str, User] = (
            backup["users"] if backup is not None else dict()
        )  # The registered users

        self.__chats: dict[str, User] = (
            backup["chats"] if backup is not None else dict()
        )  # The created chats

        self.__tokens: dict[str, User] = (
            backup["tokens"] if backup is not None else dict()
        )  # The current open sessions

        self.__redirect_chats: dict[str:str] = (
            backup["redirect_chats"] if backup is not None else dict()
        )  # Maps chat name to the respective server

        self.__n_chats_per_server: dict[str:str] = (
            backup["n_chats_per_server"]
            if backup is not None
            else {server: 0 for server in chat_servers}
        )  # The number of chats allocated to a specific server

        self.__n_requests: int = (
            backup["n_requests"] if backup is not None else 0
        )  # Number of request received (for stats)

        self.__average_latency: int = (
            backup["average_latency"] if backup is not None else 0
        )  # Average operation latency (for stats)

        self.__lock = threading.Lock()  # Thread lock

        if backup is not None:
            print(
                f"* Database backup : found ({len(self.__users)} users and {len(self.__chats)} chats)"
            )
        else:
            print("* Database backup : not found")

    ############################## Chats server management ##############################

    def get_associated_server(self, chat_name: str) -> str | None:
        with self.__lock:
            return self.__redirect_chats.get(chat_name)

    def get_lowest_load_server(self) -> str | None:
        """Returns the server with the lowest load"""
        with self.__lock:
            minimum = sys.maxsize
            min_server = None

            for server, value in self.__n_chats_per_server.items():
                if value < minimum:
                    minimum = value
                    min_server = server

            return min_server

    def associate_chat_with_server(self, chat_name: str, server: str):
        """Associates a chat with a server"""

        with self.__lock:
            self.__redirect_chats[chat_name] = server
            self.__n_chats_per_server[server] += 1

    ############################## Users management ##############################

    def exists_user(self, username: str) -> bool:
        """Checks if a user is registered"""

        with self.__lock:
            return username in self.__users

    def get_user_password(self, username: str) -> str:
        """Returns the encrypted user password"""

        with self.__lock:
            return self.__users[username].get_password()

    def create_user(
        self, username: str, password: str, already_encrypted: bool = False
    ) -> None:
        """Creates the user"""

        with self.__lock:
            self.__users[username] = User(
                username,
                self.encode_password(password) if not already_encrypted else password,
            )

    def is_password_correct(self, username: str, password: str) -> bool:
        """Checks if a user password is correct"""

        with self.__lock:
            return self.__users[username].is_password_correct(
                self.encode_password(password)
            )

    def open_user_session(self, username: str) -> str:
        """Opens a session for the user and returns the token"""

        with self.__lock:
            token = self.generate_token()
            self.__tokens[token] = self.__users[username]
            return token

    def close_user_session(self, user_token: str) -> None:
        """Closes the session of the user"""

        with self.__lock:
            self.__tokens.pop(user_token)

    def is_user_logged_in(self, user_token: str) -> bool:
        """Check if a session is opened for the user (if login was made)"""

        with self.__lock:
            return user_token in self.__tokens

    def get_list_users(self) -> list[str]:
        """Get the current users"""

        with self.__lock:
            return list(self.__users.keys())

    ############################## Chats management ##############################

    def exists_chat(self, chat_name: str) -> bool:
        """Checks if a chat with the given name already exists"""

        with self.__lock:
            return chat_name in self.__chats

    def create_chat(self, chat_name: str) -> None:
        """Creates a chat"""

        with self.__lock:
            self.__chats[chat_name] = Chat(chat_name)

    def add_user_to_chat(self, username: str, chat_name: str) -> None:
        """Adds an user to a chat"""

        with self.__lock:
            self.__chats[chat_name].add_user(self.__users[username])

    def is_user_in_chat(
        self, user: str, chat_name: str, use_token_instead: bool = False
    ) -> bool:
        """Checks if a user is in a chat, given the username or the respective token"""

        with self.__lock:
            if use_token_instead:
                return self.__tokens[user] in self.__chats[chat_name]
            else:
                return self.__users[user] in self.__chats[chat_name]

    def send_message(self, user_token: str, chat_name: str, msg: str) -> None:
        """Sends a message to a chat"""

        with self.__lock:
            self.__chats[chat_name].send_message(
                Message(self.__tokens[user_token], msg)
            )

    def get_unseen_messages(
        self, user_token: str, chat_name: str
    ) -> list[dict[str:str]]:
        """Gets the unseen messages of a user"""

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

    def get_chat_messages(self, chat_name: str) -> list[dict[str:str]]:
        """Gets all the messages in a chat"""

        with self.__lock:
            return [
                {
                    "sender": msg.get_sender().get_username(),
                    "msg": msg.get_message(),
                    "time": msg.get_time().strftime("%Y-%m-%d %H:%M:%S"),
                }
                for msg in self.__chats[chat_name].get_messages()
            ]

    def remove_user_from_chat(self, username: str, chat_name: str) -> None:
        """Removes a user from a chat"""

        with self.__lock:
            self.__chats[chat_name].remove_user(self.__users[username])

    def get_list_chats(self) -> list[str]:
        """Get the current chats"""

        with self.__lock:
            return list(self.__chats.keys())

    ############################## Utilities ##############################

    def encode_password(self, password: str) -> str:
        """Encodes a password using the SHA-256 algorithm"""

        return hashlib.sha256(bytes(password, "utf-8")).hexdigest()

    def generate_token(self) -> str:
        """Generates a token for the user session"""

        return secrets.token_hex(32)

    def backup(self) -> None:
        """Backups the database to a pickle file"""

        with self.__lock:
            backup = {
                "users": self.__users,
                "chats": self.__chats,
                "tokens": self.__tokens,
                "n_requests": self.__n_requests,
                "average_latency": self.__average_latency,
                "redirect_chats": self.__redirect_chats,
                "n_chats_per_server": self.__n_chats_per_server,
            }

            with open("backup.pickle", "wb") as f:
                pickle.dump(backup, f, pickle.HIGHEST_PROTOCOL)

    def update_average_operation_latency(self, latency: float) -> None:
        """Updates the current average operation latency"""

        with self.__lock:
            self.__n_requests += 1
            self.__average_latency += (
                latency - self.__average_latency
            ) / self.__n_requests

    def get_stats(self) -> dict[str : int | float]:
        """Gets some stats from the database"""

        with self.__lock:
            return {
                "number_of_users": len(self.__users),
                "number_of_chats": len(self.__chats),
                "number_of_sent_messages": sum(
                    [len(chat) for chat in self.__chats.values()]
                ),
                "average_operation_latency": self.__average_latency,
            }

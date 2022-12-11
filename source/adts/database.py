import hashlib
import secrets
import threading
import pickle
import os

from adts import User, Message, Chat


class Database:
    """Class representing a thread safe database of Talk2Me"""

    def __init__(self) -> None:

        # Check if there is a backup available to load from
        if os.path.exists("backup.pickle"):

            with open("backup.pickle", "rb") as f:
                backup = pickle.load(f)

            self.__users: dict[str, User] = backup["users"]
            self.__chats: dict[str, User] = backup["chats"]

            print("Loaded database from previous backup")

        else:
            self.__users: dict[str, User] = dict()  # The registered users
            self.__chats: dict[str, Chat] = dict()  # The created chats

            print("Couldn't load database from backup")

        self.__tokens: dict[str, User] = dict()  # The current open sessions
        self.__lock = threading.Lock()  # Thread lock

    ############################## Users management ##############################

    def exists_user(self, username: str) -> bool:
        """Checks if a user is registered"""

        with self.__lock:
            return username in self.__users

    def create_user(self, username: str, password: str) -> None:
        """Creates the user"""

        with self.__lock:
            self.__users[username] = User(username, self.encode_password(password))

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

    def remove_user_from_chat(self, username: str, chat_name: str) -> None:
        """Removes a user from a chat"""

        with self.__lock:
            self.__chats[chat_name].remove_user(self.__users[username])

    ############################## Others ##############################

    def get_list_users(self) -> list[str]:
        """Get the current users"""

        with self.__lock:
            return list(self.__users.keys())

    def get_list_chats(self) -> list[str]:
        """Get the current chats"""

        with self.__lock:
            return list(self.__chats.keys())

    def get_stats(self) -> dict[str : int | float]:
        """Gets some stats from the database"""

        with self.__lock:
            return {
                "number_of_users": len(self.__users),
                "number_of_chats": len(self.__chats),
                "number_of_sent_messages": sum(
                    [len(chat) for chat in self.__chats.values()]
                ),
                "average_operation_latency": 0,
            }

    ############################## Utilities ##############################

    def encode_password(self, password: str) -> str:
        """Encodes a password using the SHA-256 algorithm"""

        return hashlib.sha256(bytes(password, "utf-8")).hexdigest()

    def generate_token(self) -> str:
        """Generates a token for the user session"""

        return secrets.token_hex(32)

    def backup(self) -> None:
        with self.__lock:
            backup = {"users": self.__users, "chats": self.__chats}

            with open("backup.pickle", "wb") as f:
                pickle.dump(backup, f, pickle.HIGHEST_PROTOCOL)

from adts import User, Message


class Chat:
    """Class representing a chat"""

    def __init__(self, name: str) -> None:
        self.__name: str = name  # Name of the chat
        self.__users: set[User] = set()  # Users in the chat
        self.__messages: list[Message] = list()  # Complete list of messages sent
        self.__unseen_messages: dict[
            User : list[Message]
        ] = dict()  # List of unseen messages per user

    def get_name(self) -> str:
        """Get the name of the chat"""

        return self.__name

    def get_messages(self) -> list[Message]:
        """Get all messages in the chat"""

        return self.__messages

    def add_user(self, user: User) -> None:
        """Adds the user to the chat and initializes the unseen messages list"""

        self.__users.add(user)
        self.__unseen_messages[user] = list()

    def remove_user(self, user: User) -> None:
        """Removes user and the respective unseen messages list"""

        self.__users.remove(user)
        self.__unseen_messages.pop(user)

    def send_message(self, message: Message) -> None:
        """Sends the message to every other member of the chat"""

        self.__messages.append(message)

        for user in self.__users:
            if user != message.get_sender():
                self.__unseen_messages[user].append(message)

    def get_unseen_messages(self, user: User) -> list[Message]:
        """Returns the unseen messages of the user in this chat"""

        messages = self.__unseen_messages[user]

        self.__unseen_messages[user] = list()

        return messages

    def __repr__(self) -> str:
        """String representation of the chat"""

        return f"{self.__name} has {len(self.__users)} users and {len(self.__messages)} messages"

    def __hash__(self) -> int:
        """The chat is uniquely identified by its name"""

        return hash(self.__name)

    def __contains__(self, user: User) -> bool:
        """Check if a user is in a chat"""

        return user in self.__users

    def __len__(self) -> int:
        """The len of the chat is defined by the amount of messages sent"""

        return len(self.__messages)

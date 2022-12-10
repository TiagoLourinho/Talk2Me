from adts import User, Message


class Chat:
    def __init__(self, name: str) -> None:
        self.__name = name
        self.__users = set()
        self.__messages = list()
        self.__unseen_messages = dict()

    def get_name(self) -> str:
        return self.__name

    def add_user(self, user: User) -> None:
        self.__users.add(user)
        self.__unseen_messages[user] = list()

    def remove_user(self, user: User) -> None:
        self.__users.remove(user)
        self.__unseen_messages.pop(user)

    def send_message(self, message: Message) -> None:
        self.__messages.append(message)

        for user in self.__users:
            if user != message.get_sender():
                self.__unseen_messages[user].append(message)

    def get_unseen_messages(self, user: User) -> list[Message]:
        messages = self.__unseen_messages[user]

        self.__unseen_messages[user] = list()

        return messages

    def __repr__(self) -> str:
        return f"{self.__name} has {len(self.__users)} users and {len(self.__messages)} messages"

    def __hash__(self) -> int:
        return hash(self.__name)

    def __contains__(self, user: User) -> bool:
        return user in self.__users

    def __len__(self) -> int:
        return len(self.__messages)

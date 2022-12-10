from datetime import datetime

from adts import User


class Message:
    def __init__(self, sender: User, message: str) -> None:
        self.__sender = sender
        self.__message = message
        self.__time = datetime.now()

    def get_sender(self) -> User:
        return self.__sender

    def get_message(self) -> str:
        return self.__message

    def __repr__(self) -> str:
        return f"{self.__sender} sent '{self.__message}' at {self.__time}"

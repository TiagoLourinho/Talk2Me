from datetime import datetime

from adts import User


class Message:
    """A class representing a message sent"""

    def __init__(self, sender: User, message: str) -> None:
        self.__sender: User = sender  # The sender
        self.__message: str = message  # The message
        self.__time: datetime = datetime.now()  # The time when the message was sent

    def get_sender(self) -> User:
        """Get message sender"""

        return self.__sender

    def get_message(self) -> str:
        """Get message"""

        return self.__message

    def get_time(self) -> datetime:
        """Get time of the message"""

        return self.__time

    def __repr__(self) -> str:
        """String representation of a message"""

        return f'{self.__sender} sent "{self.__message}" at {self.__time.strftime("%Y-%m-%d %H:%M:%S")}'

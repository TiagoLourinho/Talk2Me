class Chat:
    def __init__(self, name: str) -> None:
        self.__name = name
        self.__users = set()
        self.__messages = list()
        self.__unseen_messages = dict()

    def __repr__(self) -> str:
        return f"{self.__name} has {len(self.__users)} users and {len(self.__messages)} messages"

    def __hash__(self) -> int:
        return hash(self.__name)

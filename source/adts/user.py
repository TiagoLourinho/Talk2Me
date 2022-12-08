class User:
    def __init__(self, username: str, password: str) -> None:
        self.__username = username
        self.__password = password

    def get_username(self) -> str:
        return self.__username

    def is_password_correct(self, password: str) -> bool:
        return self.__password == password

    def __repr__(self) -> str:
        return self.__username

    def __hash__(self) -> int:
        return hash(self.__username)

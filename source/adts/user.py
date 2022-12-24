import hmac


class User:
    """A class representing a user of Talk2Me"""

    def __init__(self, username: str, password: str) -> None:
        self.__username: str = username  #  The username
        self.__password: str = password  # The encrypted password

    def get_username(self) -> str:
        """Get the username"""

        return self.__username

    def get_password(self) -> str:
        """Get the password"""

        return self.__password

    def is_password_correct(self, password_digested: str) -> bool:
        """Check if the password is correct"""

        return hmac.compare_digest(self.__password, password_digested)

    def __repr__(self) -> str:
        """String representation of the user"""

        return self.__username

    def __hash__(self) -> int:
        """An user is uniquely identified by his username"""

        return hash(self.__username)

    def __eq__(self, other: "User") -> bool:
        """An user is equal to other if they have the same username"""

        return self.__username == other.__username

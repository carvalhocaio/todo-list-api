class DomainError(Exception):
    pass


class EmailAlreadyRegisteredError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class InvalidRefreshTokenError(DomainError):
    pass


class RefreshTokenReusedError(InvalidRefreshTokenError):
    pass


class TodoNotFoundError(DomainError):
    pass


class NotTodoOwnerError(DomainError):
    pass

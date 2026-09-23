from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str

from datetime import datetime, timezone


class BlacklistedToken:
    def __init__(self, jti: str, expires_at: datetime):
        if not jti or not jti.strip():
            raise ValueError("jti는 비어 있을 수 없습니다.")
        if expires_at.tzinfo is None or expires_at.utcoffset() is None:
            raise ValueError("만료 시각은 timezone 정보가 있어야 합니다.")
        self.jti = jti
        self.expires_at = expires_at

    def is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return now >= self.expires_at

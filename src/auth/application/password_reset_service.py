import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from auth.domain.exceptions import InvalidResetCodeError
from auth.domain.password_reset_code import PasswordResetCode
from auth.domain.repository.password_reset_code_repository import PasswordResetCodeRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.service import (
    Clock,
    PasswordHasher,
    PasswordResetNotifier,
    ResetCodeGenerator,
)
from auth.domain.user import User

logger = logging.getLogger("auth.password_reset")


@dataclass(frozen=True)
class ResetDelivery:
    """응답 뒤 전달할 정보. code는 repr에 드러나지 않는다."""

    email: str
    code: str = field(repr=False)
    expires_at: datetime


class PasswordResetService:
    def __init__(
        self,
        session: AsyncSession,
        users: UserRepository,
        codes: PasswordResetCodeRepository,
        hasher: PasswordHasher,
        generator: ResetCodeGenerator,
        notifier: PasswordResetNotifier,
        clock: Clock,
    ):
        self.session = session
        self.users = users
        self.codes = codes
        self.hasher = hasher
        self.generator = generator
        self.notifier = notifier
        self.clock = clock

    async def request_reset(self, email: str) -> ResetDelivery | None:
        """가입 여부와 무관하게 정상 반환한다(REQ-27). 모든 분기가 bcrypt hash를 정확히 1회 한다.

        전달할 정보만 돌려주고, 실제 전달은 응답 뒤 `deliver`가 한다.
        """
        user = await self.users.find_by_email(User.normalize_email(email))
        if user is None or not user.can_reset_password:
            self._spend_hash_cost()
            return None
        locked = await self.users.find_by_id(user.id, for_update=True)  # 회원 행 -> 코드 행 (D-잠금순서)
        if locked is None or not locked.can_reset_password:
            self._spend_hash_cost()
            return None
        now = self.clock.now()
        previous = await self.codes.find_by_user_id(user.id, for_update=True)
        if PasswordResetCode.is_request_throttled(previous, now):
            self._spend_hash_cost()  # 재요청 간격 안: 기존 코드 유지, 새 코드·알림 없음
            return None
        raw_code = self.generator.generate()
        # 회원당 1행 덮어쓰기: 이전 코드는 무효, 새 코드는 실패 횟수 0에서 시작
        code = PasswordResetCode.issue(user.id, raw_code, self.hasher, now)
        await self.codes.save(code)
        await self.session.commit()
        return ResetDelivery(email=locked.email, code=raw_code, expires_at=code.expires_at)

    async def deliver(self, delivery: ResetDelivery) -> None:
        """응답 뒤(BackgroundTasks) 실행. 전달 실패는 로그로만 남긴다."""
        try:
            await self.notifier.send_code(delivery.email, delivery.code, delivery.expires_at)
        except Exception:  # noqa: BLE001 - 전달 실패를 응답에 드러내면 가입 여부가 노출된다
            logger.exception("비밀번호 재설정 코드 전달 실패")

    def _spend_hash_cost(self) -> None:
        self.hasher.hash(self.generator.generate())  # 결과는 버린다 (D-재설정시간균등)

    async def confirm_reset(self, email: str, code: str, new_password: str) -> None:
        User.validate_raw_password(new_password)  # ① 위반이면 코드·횟수를 건드리지 않고 400
        user = await self.users.find_by_email(User.normalize_email(email))
        if user is None or not user.can_reset_password:  # ②
            self.hasher.dummy_verify(code)
            raise InvalidResetCodeError()
        locked = await self.users.find_by_id(user.id, for_update=True)  # ③ 회원 행을 먼저 잠근다
        if locked is None or not locked.can_reset_password:
            self.hasher.dummy_verify(code)
            raise InvalidResetCodeError()
        stored = await self.codes.find_by_user_id(user.id, for_update=True)  # ④ 코드 행
        if stored is None:
            self.hasher.dummy_verify(code)
            raise InvalidResetCodeError()
        if not stored.check(code, self.hasher, self.clock.now()):
            await self.codes.save(stored)  # ⑤ 실패 횟수를 남기려고 커밋한 뒤 예외
            await self.session.commit()
            raise InvalidResetCodeError()
        locked.reset_password(new_password, self.hasher)  # ⑥ 실패 횟수·잠금도 초기화
        await self.users.save(locked)
        await self.codes.delete(user.id)  # 1회용
        await self.session.commit()

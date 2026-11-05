import logging

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

    async def request_reset(self, email: str) -> None:
        """가입 여부와 무관하게 정상 반환한다(REQ-27). 미가입·탈퇴는 아무것도 하지 않는다."""
        user = await self.users.find_by_email(User.normalize_email(email))
        if user is None or not user.can_reset_password:
            self.hasher.dummy_verify("dummy-reset-code")  # 응답 시간을 맞춘다
            return
        now = self.clock.now()
        raw_code = self.generator.generate()
        previous = await self.codes.find_by_user_id(user.id, for_update=True)
        # 회원당 1행 덮어쓰기: 이전 코드는 무효, 실패 횟수는 만료 전이면 이어받는다(5회 제한 우회 방지)
        code = PasswordResetCode.issue(user.id, raw_code, self.hasher, now, previous)
        await self.codes.save(code)
        await self.session.commit()
        try:
            await self.notifier.send_code(user.email, raw_code, code.expires_at)
        except Exception:  # noqa: BLE001 - 전달 실패를 응답에 드러내면 가입 여부가 노출된다
            logger.exception("비밀번호 재설정 코드 전달 실패")

    async def confirm_reset(self, email: str, code: str, new_password: str) -> None:
        User.validate_raw_password(new_password)  # ① 위반이면 코드·횟수를 건드리지 않고 400
        user = await self.users.find_by_email(User.normalize_email(email))
        if user is None or not user.can_reset_password:  # ②
            self.hasher.dummy_verify(code)
            raise InvalidResetCodeError()
        stored = await self.codes.find_by_user_id(user.id, for_update=True)  # ③ 코드 행 -> 회원 행 순
        if stored is None:
            self.hasher.dummy_verify(code)
            raise InvalidResetCodeError()
        if not stored.check(code, self.hasher, self.clock.now()):
            await self.codes.save(stored)  # ④ 실패 횟수를 남기려고 커밋한 뒤 예외
            await self.session.commit()
            raise InvalidResetCodeError()
        locked = await self.users.find_by_id(user.id, for_update=True)  # ⑤
        if locked is None:
            raise InvalidResetCodeError()
        locked.reset_password(new_password, self.hasher)
        await self.users.save(locked)
        await self.codes.delete(user.id)  # 1회용
        await self.session.commit()

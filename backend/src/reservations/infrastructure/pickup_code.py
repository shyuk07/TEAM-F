import secrets
import string

from reservations.domain import rules
from reservations.domain.service import PickupCodeGenerator


class SecretsPickupCodeGenerator(PickupCodeGenerator):
    def generate(self) -> str:
        letters = "".join(secrets.choice(string.ascii_uppercase) for _ in range(rules.PICKUP_CODE_LETTERS))
        digits = "".join(secrets.choice(string.digits) for _ in range(rules.PICKUP_CODE_DIGITS))
        return letters + digits

"""OTP / reset delivery — the AccountService hands the code to a Notifier."""

from __future__ import annotations

from app.core.notifications import ConsoleSender, Notifier, build_notifier
from app.core.security import hash_password
from app.repositories.auth_token_repository import InMemoryAuthTokenRepository
from app.repositories.user_repository import InMemoryUserRepository
from app.services.account_service import AccountService


class SpyNotifier(Notifier):
    """Records what would have been sent instead of sending it."""

    def __init__(self):
        self.sms = []   # list[(to, message)]
        self.email = []  # list[(to, subject, body)]

    def send_sms(self, to, message):
        self.sms.append((to, message))

    def send_email(self, to, subject, body):
        self.email.append((to, subject, body))


def _user(users, mobile="9000000123"):
    return users.add_user("Otto OTP", "otto", mobile, hash_password("secret123"), "player")


def test_verification_code_is_delivered_by_sms():
    users = InMemoryUserRepository()
    user = _user(users)
    spy = SpyNotifier()
    svc = AccountService(users, InMemoryAuthTokenRepository(), notifier=spy)

    code = svc.request_verification(user)

    assert spy.sms, "an SMS should have been sent"
    to, message = spy.sms[0]
    assert to == user.mobile_no
    assert code in message  # the code reaches the user
    # and the issued code still verifies
    svc.confirm_verification(user, code)
    assert users.get_by_identifier("otto").is_verified is True


def test_reset_code_is_delivered_to_the_matching_user_only():
    users = InMemoryUserRepository()
    _user(users)
    spy = SpyNotifier()
    svc = AccountService(users, InMemoryAuthTokenRepository(), notifier=spy)

    token = svc.request_reset("otto")
    assert token and spy.sms and token in spy.sms[0][1]

    spy.sms.clear()
    assert svc.request_reset("ghost") is None  # unknown user
    assert spy.sms == []  # nothing sent — no account enumeration


def test_verification_goes_to_email_when_user_has_one():
    users = InMemoryUserRepository()
    user = users.add_user("Eva Email", "eva", "9000000999", hash_password("secret123"),
                          "player", email="eva@example.com")
    spy = SpyNotifier()
    svc = AccountService(users, InMemoryAuthTokenRepository(), notifier=spy)

    code = svc.request_verification(user)

    assert spy.email and not spy.sms, "should deliver by email, not SMS"
    to, subject, body = spy.email[0]
    assert to == "eva@example.com" and code in body


def test_reset_goes_to_email_when_user_has_one():
    users = InMemoryUserRepository()
    users.add_user("Eva Email", "eva", "9000000999", hash_password("secret123"),
                   "player", email="eva@example.com")
    spy = SpyNotifier()
    svc = AccountService(users, InMemoryAuthTokenRepository(), notifier=spy)

    token = svc.request_reset("eva")
    assert token and spy.email and not spy.sms
    assert spy.email[0][0] == "eva@example.com" and token in spy.email[0][2]


def test_console_sender_and_default_factory_never_raise():
    ConsoleSender().sms("9000000000", "hi")
    ConsoleSender().email("a@b.c", "subj", "body")
    # with no provider env set, the factory falls back to console for both
    n = build_notifier()
    assert isinstance(n.sms_backend, ConsoleSender)
    assert isinstance(n.email_backend, ConsoleSender)


def test_notifier_swallows_backend_failure():
    class Boom:
        def sms(self, *a):
            raise RuntimeError("provider down")

    n = Notifier(sms_backend=Boom())
    n.send_sms("9000000000", "x")  # must not raise

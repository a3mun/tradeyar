import requests
from sqlmodel import Session, select
from api.database import engine
from api.models import User

BASE_URL = "http://127.0.0.1:8000"


def test_admin_security():
    # لاگین با شماره 0937
    res = requests.post(f"{BASE_URL}/auth/send-otp", json={"phone": "09371069753"})
    print("Send OTP user:", res.status_code)

    # چک کردن دیتابیس
    with Session(engine) as session:
        user = session.exec(select(User).where(User.phone == "09371069753")).first()
        if user:
            print(f"User 0937 is_admin: {user.is_admin}")
            assert user.is_admin == False, "❌ کاربر 0937 نباید ادمین باشه!"
        else:
            print("User 0937 not found")

    print("✅ تست امنیتی موفق بود")


if __name__ == "__main__":
    test_admin_security()

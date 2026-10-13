import re
from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

PHONE_RE = re.compile(r"^\+?[0-9 \-]{8,16}$")
UPI_RE = re.compile(r"^[A-Za-z0-9._-]{2,40}@[A-Za-z][A-Za-z0-9]{1,20}$")


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        if v and not PHONE_RE.match(v):
            raise ValueError("Enter a valid phone number.")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=72)


class ProfileIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone: str | None = None
    dob: Date | None = None
    gender: Literal["Female", "Male", "Other", ""] | None = None
    nationality: str | None = Field(default=None, max_length=40)
    passport_no: str | None = Field(default=None, max_length=12)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        if v and not PHONE_RE.match(v):
            raise ValueError("Enter a valid phone number.")
        return v or None


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class PassengerIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    age: int = Field(ge=2, le=120)
    gender: Literal["Female", "Male", "Other"] | None = None
    passport_no: str | None = None
    seat_no: str = Field(min_length=2, max_length=4)


class BookingIn(BaseModel):
    flight_id: int
    passengers: list[PassengerIn] = Field(min_length=1, max_length=9)
    contact_email: EmailStr
    contact_phone: str
    promo_code: str | None = None

    @field_validator("contact_phone")
    @classmethod
    def _phone(cls, v):
        if not PHONE_RE.match(v):
            raise ValueError("Enter a valid contact phone number.")
        return v


class PromoIn(BaseModel):
    code: str
    flight_id: int
    seat_nos: list[str] = []


class PaymentStartIn(BaseModel):
    pnr: str
    method: Literal["UPI", "CARD", "NETBANKING"]
    upi_id: str | None = None
    card_number: str | None = None
    card_name: str | None = None
    card_expiry: str | None = None      # MM/YY
    card_cvv: str | None = None
    bank: str | None = None


class SandboxResolveIn(BaseModel):
    outcome: Literal["approve", "decline"]


class AlertIn(BaseModel):
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    travel_date: Date
    flight_id: int | None = None
    target_price: float | None = Field(default=None, gt=0)
    email: EmailStr | None = None

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str | None = None
    timezone: str | None = "UTC"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str | None
    timezone: str | None
    auth_provider: str
    profile_picture_url: str | None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmailPreferencesResponse(BaseModel):
    email_notifications_enabled: bool
    calendar_email_reminders_enabled: bool
    favorite_driver_email_alerts_enabled: bool

    model_config = {"from_attributes": True}


class EmailPreferencesUpdate(BaseModel):
    email_notifications_enabled: bool | None = None
    calendar_email_reminders_enabled: bool | None = None
    favorite_driver_email_alerts_enabled: bool | None = None


class NotificationPreferencesResponse(BaseModel):
    favorite_driver_notifications_enabled: bool
    favorite_driver_email_alerts_enabled: bool

    model_config = {"from_attributes": True}


class NotificationPreferencesUpdate(BaseModel):
    favorite_driver_notifications_enabled: bool | None = None
    favorite_driver_email_alerts_enabled: bool | None = None


class UserProfileUpdate(BaseModel):
    username: str | None = None
    timezone: str | None = None

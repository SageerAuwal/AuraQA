import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.models import User
from app.schemas.user import UserRegister, UserLogin, UserOut, Token

router = APIRouter()

# Account lockout configuration
MAX_FAILED_ATTEMPTS = 5          # Lock after 5 consecutive wrong passwords
LOCKOUT_DURATION_MINUTES = 15    # Stay locked for 15 minutes


def _check_and_handle_lockout(user: User, db: Session):
    """
    Check if a user account is currently locked.
    Raises HTTP 403 if still locked, otherwise returns silently.
    """
    if user.locked_until and datetime.datetime.utcnow() < user.locked_until:
        remaining = int((user.locked_until - datetime.datetime.utcnow()).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked due to too many failed attempts. Try again in {remaining} minute(s)."
        )


def _record_failed_attempt(user: User, db: Session):
    """
    Increment failed login counter. Lock the account if threshold is reached.
    """
    user.failed_attempts = (user.failed_attempts or 0) + 1
    if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.datetime.utcnow() + datetime.timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    db.commit()


def _reset_failed_attempts(user: User, db: Session):
    """
    Reset the failed login counter and unlock the account on successful login.
    """
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """Register a new user in the system."""
    # Check if user with same email exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
    
    # Create and commit new user record
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        failed_attempts=0,
        locked_until=None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible token login (form data), making OpenAPI/Swagger UI login feature work."""
    user = db.query(User).filter(User.email == form_data.username).first()

    # Return generic error if user not found (prevents email enumeration)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if account is currently locked
    _check_and_handle_lockout(user, db)

    # Validate password
    if not verify_password(form_data.password, user.password_hash):
        _record_failed_attempt(user, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Success — reset lockout counter and issue token
    _reset_failed_attempts(user, db)
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/json", response_model=Token)
def login_json(
    login_in: UserLogin,
    db: Session = Depends(get_db)
):
    """JSON-body based login route (ideal for standard frontend framework calls)."""
    user = db.query(User).filter(User.email == login_in.email).first()

    # Return generic error if user not found (prevents email enumeration)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if account is currently locked
    _check_and_handle_lockout(user, db)

    # Validate password
    if not verify_password(login_in.password, user.password_hash):
        _record_failed_attempt(user, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Success — reset lockout counter and issue token
    _reset_failed_attempts(user, db)
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Fetch the authenticated user's profile."""
    return current_user

import os
import sys

# Ensure the backend directory is in the Python PATH
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

from app.core.security import hash_password, verify_password
from app.core.database import SessionLocal, Base, engine
from app.models.models import User

def test_security():
    print("Testing password hashing and verification...")
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password, "Hashed password should not equal plain password"
    assert verify_password(password, hashed), "Password verification failed"
    assert not verify_password("wrong_password", hashed), "Should fail with wrong password"
    print("[OK] Password hashing and verification passed.")

def test_database():
    print("Testing database connection, table creation, and CRUD...")
    # Create all tables (will create chatbot.db if using SQLite)
    Base.metadata.create_all(bind=engine)
    
    # Create database session
    db = SessionLocal()
    try:
        test_email = "verification_test@example.com"
        
        # Delete if user already exists from a previous failed run
        existing = db.query(User).filter(User.email == test_email).first()
        if existing:
            db.delete(existing)
            db.commit()
            
        # Create test user
        hashed = hash_password("MySecurePass!")
        user = User(name="Verifier Admin", email=test_email, password_hash=hashed)
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.id is not None, "Failed to auto-generate user primary key ID"
        assert user.name == "Verifier Admin", "Saved user name does not match input"
        print(f"[OK] Database connection and user insertion succeeded. Created User ID: {user.id}")
        
        # Cleanup user record
        db.delete(user)
        db.commit()
        print("[OK] Database cleanup completed successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Starting Phase 1 Integration Verification ===")
    try:
        test_security()
        test_database()
        print("=== Verification Successful! ===")
    except Exception as e:
        print(f"[ERROR] Verification failed with error: {e}", file=sys.stderr)
        sys.exit(1)

"""
Authentication Service.
Handles user authentication, JWT token management, and password hashing.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel


# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: int
    email: str
    role: str
    exp: datetime


class AuthService:
    """
    Service for handling authentication operations.
    Implements secure password hashing and JWT token management.
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    @staticmethod
    def create_access_token(
        user_id: int,
        email: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            user_id: User's unique identifier
            email: User's email address
            role: User's role (candidate/recruiter)
            expires_delta: Optional custom expiration time
            
        Returns:
            Encoded JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Optional[TokenData]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return TokenData(
                user_id=payload.get("user_id"),
                email=payload.get("email"),
                role=payload.get("role"),
                exp=datetime.fromtimestamp(payload.get("exp"))
            )
        except JWTError:
            return None
    
    @staticmethod
    def is_token_expired(token_data: TokenData) -> bool:
        """Check if a token is expired."""
        return datetime.utcnow() > token_data.exp
    
    @staticmethod
    def refresh_token(token: str) -> Optional[str]:
        """
        Refresh an existing token if it's still valid.
        
        Args:
            token: Current JWT token
            
        Returns:
            New token if successful, None if invalid
        """
        token_data = AuthService.decode_token(token)
        
        if token_data is None or AuthService.is_token_expired(token_data):
            return None
        
        return AuthService.create_access_token(
            user_id=token_data.user_id,
            email=token_data.email,
            role=token_data.role
        )

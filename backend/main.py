import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from passlib.context import CryptContext
from jose import jwt, JWTError
from openai import OpenAI
from fastapi.responses import StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET not found")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
security = HTTPBearer()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)


Base.metadata.create_all(bind=engine)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    assert JWT_SECRET is not None, "JWT_SECRET must not be None"
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if JWT_SECRET is None:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not set")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


class SignupRequest(BaseModel):
    name: str
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class GenerateTextRequest(BaseModel):
    prompt: str


@app.post("/create-user")
def create_user(data: SignupRequest):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            (User.username == data.username) |
            (User.email == data.email)
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        user = User(
            name=data.name,
            username=data.username,
            email=data.email,
            password=hash_password(data.password)
        )

        db.add(user)
        db.commit()
        return {"message": "User created successfully"}

    finally:
        db.close()


@app.post("/login")
def login_user(data: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.username == data.username
        ).first()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        hashed_password = getattr(user, 'password', None)
        if not hashed_password or not verify_password(data.password, hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({"sub": user.username})

        return {
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer"
        }

    finally:
        db.close()


SYSTEM_PROMPT = """
You are Brian, a friendly AI assistant created by AswinCreates (https://aswinrout.is-a.dev/).

Rules:
- Your name is Brian.
- Never say you are OpenAI, ChatGPT, or a language model.
- You help college students with coding, AI, and projects.
- Be concise, friendly, and professional.
"""

@app.post("/generate-text")
def generate_text(data: GenerateTextRequest, user=Depends(verify_token)):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def stream():
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": data.prompt}
            ],
            stream=True
        )

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return StreamingResponse(stream(), media_type="text/plain")


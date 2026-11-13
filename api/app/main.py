from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError
from typing import Optional, List
from datetime import datetime, timedelta
import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, select
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import OperationalError

# Configuración de variables de entorno y constantes
AUTH_SECRET = os.getenv("AUTH_SECRET") or os.getenv("JWT_SECRET") or "secret_jwt_key_default"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 día

DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql+psycopg://studio:studio@localhost:5432/producto"

# Intentar conectar a PostgreSQL, si falla usar SQLite local
try:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
    # Probar conexión
    with engine.connect() as conn:
        conn.execute(select(1))
except OperationalError:
    # Fallback a SQLite local
    DATABASE_URL = "sqlite:///./app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelos SQLAlchemy
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    full_name = Column(String(100), nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=True)
    disabled = Column(Boolean, default=False)
    role = Column(String(20), default="user")  # roles: admin, user
    created_at = Column(DateTime, default=datetime.utcnow)

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    precio = Column(Integer, nullable=False)
    creado_por = Column(Integer, nullable=False)  # user id
    creado_en = Column(DateTime, default=datetime.utcnow)

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Pydantic Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    role: str = "user"

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    hashed_password: str

class UserResponse(UserBase):
    id: int

    class Config:
        orm_mode = True

class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: int

class ProductoCreate(ProductoBase):
    pass

class ProductoResponse(ProductoBase):
    id: int
    creado_por: int
    creado_en: datetime

    class Config:
        orm_mode = True

# Seguridad y autenticación
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", scopes={"admin": "Acceso de administrador", "user": "Acceso de usuario"})

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, username: str) -> Optional[UserInDB]:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user:
        return UserInDB(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            role=user.role,
            hashed_password=user.hashed_password,
        )
    return None

def authenticate_user(db: Session, username: str, password: str) -> Optional[UserInDB]:
    user = get_user(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, AUTH_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme), db: Session = Depends(lambda: SessionLocal())):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(token, AUTH_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except (JWTError, ValidationError):
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No tiene permisos suficientes",
                headers={"WWW-Authenticate": authenticate_value},
            )
    if user.disabled:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return user

async def get_current_active_user(current_user: UserInDB = Security(get_current_user, scopes=["user"])):
    return current_user

async def get_current_active_admin(current_user: UserInDB = Security(get_current_user, scopes=["admin"])):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado como administrador")
    return current_user

# FastAPI app
app = FastAPI(title="YERUZZA STUDIO API")

# CORS (permitir frontend local y producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar en producción a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependencia para DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Rutas públicas
@app.get("/health", tags=["salud"])
def health():
    return {"status": "ok"}

@app.post("/auth/register", response_model=UserResponse, tags=["auth"])
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.execute(select(User).where(User.username == user.username)).scalar_one_or_none()
    if db_user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    db_email = None
    if user.email:
        db_email = db.execute(select(User).where(User.email == user.email)).scalar_one_or_none()
        if db_email:
            raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role if user.role in ("user", "admin") else "user",
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/auth/login", response_model=Token, tags=["auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    scopes = [user.role]
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": scopes}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserResponse, tags=["auth"])
def read_users_me(current_user: UserInDB = Security(get_current_user, scopes=["user"]), db: Session = Depends(get_db)):
    db_user = db.execute(select(User).where(User.username == current_user.username)).scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db_user

# Rutas CRUD para Producto (protegidas)
@app.post("/api/productos", response_model=ProductoResponse, tags=["productos"])
def create_producto(producto: ProductoCreate, current_user: UserInDB = Security(get_current_user, scopes=["user"]), db: Session = Depends(get_db)):
    db_producto = Producto(
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        precio=producto.precio,
        creado_por=db.execute(select(User).where(User.username == current_user.username)).scalar_one().id,
    )
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

@app.get("/api/productos", response_model=List[ProductoResponse], tags=["productos"])
def read_productos(skip: int = 0, limit: int = 100, current_user: UserInDB = Security(get_current_user, scopes=["user"]), db: Session = Depends(get_db)):
    productos = db.execute(select(Producto).offset(skip).limit(limit)).scalars().all()
    return productos

@app.get("/api/productos/{producto_id}", response_model=ProductoResponse, tags=["productos"])
def read_producto(producto_id: int, current_user: UserInDB = Security(get_current_user, scopes=["user"]), db: Session = Depends(get_db)):
    producto = db.execute(select(Producto).where(Producto.id == producto_id)).scalar_one_or_none()
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@app.put("/api/productos/{producto_id}", response_model=ProductoResponse, tags=["productos"])
def update_producto(producto_id: int, producto_update: ProductoCreate, current_user: UserInDB = Security(get_current_user, scopes=["user"]), db: Session = Depends(get_db)):
    producto = db.execute(select(Producto).where(Producto.id == producto_id)).scalar_one_or_none()
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    # Solo el creador o admin puede modificar
    user_db = db.execute(select(User).where(User.username == current_user.username)).scalar_one()
    if producto.creado_por != user_db.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado para modificar este producto")
    producto.nombre = producto_update.nombre
    producto.descripcion = producto_update.descripcion
    producto.precio = producto_update.precio
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto

@app.delete("/api/productos/{producto_id}", status_code=204, tags=["productos"])
def delete_producto(producto_id: int, current_user: UserInDB = Security(get_current_user, scopes=["user"]), db: Session = Depends(get_db)):
    producto = db.execute(select(Producto).where(Producto.id == producto_id)).scalar_one_or_none()
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    user_db = db.execute(select(User).where(User.username == current_user.username)).scalar_one()
    if producto.creado_por != user_db.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No autorizado para eliminar este producto")
    db.delete(producto)
    db.commit()
    return

# Ruta admin ejemplo para listar usuarios
@app.get("/api/users", response_model=List[UserResponse], tags=["admin"])
def read_users(skip: int = 0, limit: int = 100, current_user: UserInDB = Security(get_current_user, scopes=["admin"]), db: Session = Depends(get_db)):
    users = db.execute(select(User).offset(skip).limit(limit)).scalars().all()
    return users
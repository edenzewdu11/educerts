from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
import uuid
import csv
import io
import datetime
from xhtml2pdf import pisa
from io import BytesIO

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from datetime import timedelta

import models, schemas, crypto_utils, database, auth_utils

# Create tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="EduCerts API")
templates = Jinja2Templates(directory="templates")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for debugging CORS issues
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"VALIDATION ERROR: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    print(f"GLOBAL ERROR: {exc}")
    print(traceback.format_exc())
    return Response(
        content=f"Internal Server Error: {str(exc)}\n{traceback.format_exc()}",
        status_code=500,
        media_type="text/plain"
    )

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to EduCerts API"}

@app.post("/api/signup")
def signup(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    print(f"DEBUG: Signup request received for email: {user_data.email}")
    try:
        # Check if email exists
        db_user_email = db.query(models.User).filter(models.User.email == user_data.email).first()
        if db_user_email:
            print("DEBUG: Email already registered")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check if username/name exists
        db_user_name = db.query(models.User).filter(models.User.name == user_data.name).first()
        if db_user_name:
            print("DEBUG: Name already taken")
            raise HTTPException(status_code=400, detail="Name already taken")
        
        print("DEBUG: Hashing password...")
        hashed_password = auth_utils.get_password_hash(user_data.password)
        
        print("DEBUG: Creating user record...")
        new_user = models.User(
            name=user_data.name,
            email=user_data.email,
            password=hashed_password,
            is_admin=False
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(f"DEBUG: User created successfully with ID: {new_user.id}")
        return {"id": new_user.id, "name": new_user.name, "email": new_user.email}
    except Exception as e:
        print(f"DEBUG: Signup ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise e

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print(f"DEBUG: Login attempt for username: {form_data.username}")
    # OAuth2PasswordRequestForm uses 'username' field, we check if it matches name OR email
    user = db.query(models.User).filter(
        (models.User.name == form_data.username) | (models.User.email == form_data.username)
    ).first()
    
    if not user:
        print("DEBUG: User not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or email",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"DEBUG: User found: {user.name}. Verifying password...")
    if not auth_utils.verify_password(form_data.password, user.password):
        print("DEBUG: Password verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print("DEBUG: Login successful. Generating token...")
    access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        data={"sub": user.name}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": user.id, "name": user.name, "is_admin": user.is_admin}}

@app.post("/api/issue", response_model=schemas.Certificate)
def issue_certificate(cert_data: schemas.CertificateCreate, db: Session = Depends(get_db)):
    # 1. Prepare data payload
    payload = cert_data.data_payload
    # Add metadata to payload if needed, e.g. timestamp, issuer info
    
    # 2. Sign the data
    signature = crypto_utils.sign_data(payload)
    
    # 3. Create DB record
    # For demo, we might need to find or create a user. 
    # Let's assume student_id is passed or we create a dummy user? 
    # For now, let's treat student_name as the primary identifier for simplicity in this proto.
    
    # Create a unique ID for the cert
    cert_id = str(uuid.uuid4())
    
    db_cert = models.Certificate(
        id=cert_id,
        student_name=cert_data.student_name,
        course_name=cert_data.course_name,
        data_payload=payload,
        signature=signature
    )
    db.add(db_cert)
    db.commit()
    db.refresh(db_cert)
    return db_cert

@app.post("/api/verify")
def verify_certificate(request: schemas.VerificationRequest, db: Session = Depends(get_db)):
    # Case A: Verify by ID (re-fetch from DB)
    if request.certificate_id:
        cert = db.query(models.Certificate).filter(models.Certificate.id == request.certificate_id).first()
        if not cert:
            raise HTTPException(status_code=404, detail="Certificate not found")
        
        if cert.revoked:
             return {"valid": False, "reason": "Certificate has been revoked"}
             
        # Verify integrity
        is_valid = crypto_utils.verify_signature(cert.data_payload, cert.signature)
        return {"valid": is_valid, "certificate": cert}
    
    # Case B: Verify raw data (if provided)
    if request.data_payload and request.signature:
        is_valid = crypto_utils.verify_signature(request.data_payload, request.signature)
        return {"valid": is_valid}

    raise HTTPException(status_code=400, detail="Must provide certificate_id or data+signature")

@app.get("/api/certificates/{student_name}", response_model=List[schemas.Certificate])
def get_student_certificates(student_name: str, db: Session = Depends(get_db)):
    certs = db.query(models.Certificate).filter(models.Certificate.student_name == student_name).all()
    return certs

@app.post("/api/import")
async def import_data(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")
    
    content = await file.read()
    decoded_content = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(decoded_content))
    
    data = []
    for row in csv_reader:
        # Basic validation: ensure required fields exist
        if "student_name" in row and "course_name" in row:
            data.append(row)
        
    return {"message": "Data imported successfully", "count": len(data), "data": data}

@app.get("/api/download/{cert_id}")
def download_certificate(cert_id: str, db: Session = Depends(get_db)):
    cert = db.query(models.Certificate).filter(models.Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
        
    # Render HTML template
    template = templates.get_template("certificate.html")
    html_content = template.render(
        student_name=cert.student_name,
        course_name=cert.course_name,
        issued_at=cert.issued_at.strftime("%Y-%m-%d"),
        cert_id=cert.id,
        signature=cert.signature[:30] + "..." # Truncate for display or show full
    )
    
    # Convert to PDF
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_content.encode("utf-8")), result)
    
    if pdf.err:
        raise HTTPException(status_code=500, detail="Error generating PDF")
        
    return Response(content=result.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=cert_{cert.id}.pdf"})

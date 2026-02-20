import hashlib
import json
from jose import jws
from jose.constants import ALGORITHMS

# We will use HS256 for simplicity in this demo, but for a real "OpenCerts" like structure
# you'd use asymmetric keys (RSA/ECDSA). Let's simulate that with a shared secret or
# generated keys if we want to go full robust.
# For this implementation, let's use a generated RSA key pair for the issuer.

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import base64

# Generate a global issuer key for demonstration purposes
# In a real app, this would be loaded from a secure environment variable or KMS
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
public_key = private_key.public_key()

def get_public_key_pem():
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

def hash_data(data: dict) -> bytes:
    """Canonicalize and hash the data dictionary."""
    # Sort keys to ensure consistent ordering for hashing
    canonical_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(canonical_json.encode('utf-8')).digest()
    return digest

def sign_data(data: dict) -> str:
    """Sign the hash of the data using the issuer's private key."""
    data_hash = hash_data(data)
    signature = private_key.sign(
        data_hash,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def verify_signature(data: dict, signature_b64: str) -> bool:
    """Verify the signature against the data using the issuer's public key."""
    try:
        data_hash = hash_data(data)
        signature = base64.b64decode(signature_b64)
        public_key.verify(
            signature,
            data_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except (InvalidSignature, Exception):
        return False

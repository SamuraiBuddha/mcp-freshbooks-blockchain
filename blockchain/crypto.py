"""Cryptographic utilities for blockchain operations."""

import hashlib
import json
import time
import uuid
from typing import List, Tuple, Optional, Any, Dict
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import base64


class CryptoHelper:
    """Cryptographic helper for blockchain operations."""
    
    def __init__(self):
        self.backend = default_backend()
        self._private_key: Optional[rsa.RSAPrivateKey] = None
        self._public_key: Optional[rsa.RSAPublicKey] = None
    
    def generate_transaction_id(self, instance_id: str = "default") -> str:
        """Generate unique transaction ID with microsecond precision."""
        timestamp_micros = int(time.time() * 1_000_000)
        unique_component = str(uuid.uuid4()).split('-')[0]
        return f"{timestamp_micros}-{instance_id}-{unique_component}"
    
    def calculate_hash(self, data: Any) -> str:
        """Calculate SHA256 hash of data."""
        if isinstance(data, dict):
            data_string = json.dumps(data, sort_keys=True)
        else:
            data_string = str(data)
        
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def calculate_merkle_root(self, transactions: List[Dict[str, Any]]) -> str:
        """Calculate Merkle root of transactions."""
        if not transactions:
            return self.calculate_hash("")
        
        # Convert transactions to hashes
        hashes = [self.calculate_hash(tx) for tx in transactions]
        
        # Build Merkle tree
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])  # Duplicate last hash if odd number
            
            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hashes.append(self.calculate_hash(combined))
            
            hashes = new_hashes
        
        return hashes[0]
    
    def generate_keypair(self) -> Tuple[str, str]:
        """Generate RSA keypair for signing transactions."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=self.backend
        )
        
        public_key = private_key.public_key()
        
        # Serialize keys to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return (
            private_pem.decode('utf-8'),
            public_pem.decode('utf-8')
        )
    
    def load_private_key(self, private_key_pem: str) -> None:
        """Load private key from PEM string."""
        self._private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=self.backend
        )
        self._public_key = self._private_key.public_key()
    
    def sign_data(self, data: Dict[str, Any]) -> str:
        """Sign data with private key."""
        if not self._private_key:
            raise ValueError("Private key not loaded")
        
        data_string = json.dumps(data, sort_keys=True)
        data_bytes = data_string.encode('utf-8')
        
        signature = self._private_key.sign(
            data_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_signature(self, data: Dict[str, Any], signature: str, public_key_pem: str) -> bool:
        """Verify signature with public key."""
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=self.backend
            )
            
            data_string = json.dumps(data, sort_keys=True)
            data_bytes = data_string.encode('utf-8')
            signature_bytes = base64.b64decode(signature)
            
            public_key.verify(
                signature_bytes,
                data_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
    
    def encrypt_sensitive_data(self, data: str, key: bytes) -> str:
        """Encrypt sensitive data like API keys."""
        # Implement AES encryption for sensitive data
        # For now, return base64 encoded (implement proper encryption)
        return base64.b64encode(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str, key: bytes) -> str:
        """Decrypt sensitive data."""
        # Implement AES decryption
        # For now, return base64 decoded (implement proper decryption)
        return base64.b64decode(encrypted_data).decode()
# Cryptographic Algorithms
from Crypto.PublicKey import RSA, DSA  # For RSA and DSA key pair generation
from Crypto.Signature import pkcs1_15, DSS  # for RSA and DSA signature
from Crypto.Cipher import PKCS1_OAEP, AES  # For RSA and AES encryption
from Crypto.Hash import SHA256, HMAC  # for hashig and HMAC
from Crypto.Random import get_random_bytes  # For random bytes
from Crypto.Util.Padding import pad, unpad # For padding
from Crypto.Util import Counter # For CTC mode
import bcrypt # For password and salting
import base64
from datetime import datetime

# Standard Libraries
import os  # for file operations
import hashlib  # for hashing
import json # for database storage
import threading

def aes_encrypt_file(file_path, key):
    try:
        # Generate a random 8-byte nonce for CTR mode
        nonce = get_random_bytes(8)
        ctr = Counter.new(64, prefix=nonce, initial_value=0)

        cipher = AES.new(key, AES.MODE_CTR, counter=ctr)

        # Read plaintext and encrypt
        with open(file_path, 'rb') as file:
            plaintext = file.read()
            ciphertext = cipher.encrypt(plaintext)

        # Generate HMAC for integrity
        hmac = HMAC.new(key, ciphertext, SHA256)
        hmac_digest = hmac.digest()

        # Save nonce, ciphertext, and HMAC
        encrypted_file_path = file_path + ".enc"
        with open(encrypted_file_path, 'wb') as enc_file:
            enc_file.write(nonce)  # Store nonce first
            enc_file.write(ciphertext)  # Store encrypted data
            enc_file.write(hmac_digest)  # Append HMAC

        return encrypted_file_path
    except Exception as e:
        raise ValueError(f"Encryption failed: {e}")

def aes_decrypt_file(encrypted_file_path, key):
    try:
        # Read encrypted file
        with open(encrypted_file_path, 'rb') as enc_file:
            nonce = enc_file.read(8)  # Read 8-byte nonce
            ciphertext = enc_file.read(-32)  # Read ciphertext
            stored_hmac = enc_file.read()  # Read the HMAC

        # Verify HMAC for integrity
        hmac = HMAC.new(key, ciphertext, SHA256)
        try:
            hmac.verify(stored_hmac)
        except ValueError:
            raise ValueError("HMAC verification failed. Data may have been tampered with.")

        # Create counter from nonce
        ctr = Counter.new(64, prefix=nonce, initial_value=0)

        # Decrypt ciphertext
        cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
        decrypted_data = cipher.decrypt(ciphertext)

        # Save decrypted file
        decrypted_file_path = encrypted_file_path[:-4] 
        with open(decrypted_file_path, 'wb') as dec_file:
            dec_file.write(decrypted_data)

        return decrypted_file_path
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")

def generate_AES_key():
    try:
        key = get_random_bytes(32)
        return key
    except Exception as e:
        raise ValueError(f"Key generation failed: {e}")

# General Hashing using SHA 256  (AES already implemented with HMAC)
def hash_file(file_path):
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, 'rb') as file:
            for byte_block in iter(lambda: file.read(4096), b""): 
                sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
    except FileNotFoundError:
        return "File Not Found"
    except Exception as e:
        return f"An error occurred: {e}"

# Password functions
def store_password(username, password, filename="db_pw.json"):
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    # Load existing users from JSON file
    data = load_json(filename)
    if data is None:
        data = {}

    # Add new user with hashed password
    data[username] = hashed_password
    
    # Save back to the JSON file
    save_json(data, filename)

def load_stored_password(username, filename="db_pw.json"):
    data = load_json(filename)
    if data and username in data:
        return data[username]
    return None

def verify_password(username, password, filename="db_pw.json"):
    stored_hash = load_stored_password(username, filename)
    if stored_hash is None:
        return False
    return bcrypt.checkpw(password.encode(), stored_hash.encode())

# JSON utility functions
def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {filename}")
        return None
    except Exception as e:
        print(f"Unexpected error when loading {filename}: {e}")
        return None

def save_json(data, filename):
    try:
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
    except OSError as e:
        print(f"Error saving JSON file: {e}")

# Database functions
database_lock = threading.Lock()

def load_database(filename="db_filepaths.json"):
    try:
        with database_lock:
            data = load_json(filename) or {}
            if "file_index" not in data:
                data["file_index"] = {}
            if "peers" not in data:
                data["peers"] = {}
            if "incoming_requests" not in data:
                data["incoming_requests"] = {}
            return data
    except Exception as e:
        print(f"Error loading database: {e}")
        return {"file_index": {}, "peers": {}, "incoming_requests": {}}

def save_database(data, filename="db_filepaths.json"):
    try:
        with database_lock:
            save_json(data, filename)
    except Exception as e:
        print(f"Error saving database: {e}")

# RSA Functions
def generate_RSA_keypair(key_size=2048):
    key = RSA.generate(key_size)
    private_key = key.export_key()
    public_key = key.publickey().export_key()
    return private_key, public_key

def rsa_encrypt(data, public_key):
    pub_key = RSA.import_key(public_key)
    cipher = PKCS1_OAEP.new(pub_key)
    encrypted = cipher.encrypt(data)
    return encrypted

def rsa_decrypt(ciphertext, private_key):
    priv_key = RSA.import_key(private_key)
    cipher = PKCS1_OAEP.new(priv_key)
    decrypted = cipher.decrypt(ciphertext)
    return decrypted

def sign_data_rsa(data, private_key):
    priv_key = RSA.import_key(private_key)
    hash_obj = hashlib.sha256(data).digest()
    signature = pkcs1_15.new(priv_key).sign(hash_obj)
    return signature

def verify_signature_rsa(data, signature, public_key):
    pub_key = RSA.import_key(public_key)
    hash_obj = hashlib.sha256(data).digest()
    try:
        pkcs1_15.new(pub_key).verify(hash_obj, signature)
        return True
    except (ValueError, TypeError):
        return False

# DSA Functions
def generate_DSA_keypair(key_size=2048):
    pass

def sign_data_dsa(data, private_key):
    pass

def verify_signature_dsa(data, signature, public_key):
    pass

# Key Storage functions
def save_key(key, file_path="keys.json"):
    data = load_json(file_path) or {}
    data[file_path] = base64.b64encode(key).decode('utf-8')  # Save as base64 string
    
    save_json(data, file_path)

def load_key(file_path="keys.json"):
    data = load_json(file_path)
    if data and file_path in data:
        return base64.b64decode(data[file_path])
    return None

def get_current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Key Exchange functions

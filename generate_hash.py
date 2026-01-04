import bcrypt

password = "test123"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(f"Hash bcrypt pour '{password}':")
print(hashed.decode('utf-8'))
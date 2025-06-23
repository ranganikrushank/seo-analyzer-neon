import secrets

# Generate a random URL-safe text string, e.g. for Flask/Django secret key
secret_key = secrets.token_urlsafe(32)  # 32 bytes = 43 chars approx
print(secret_key)

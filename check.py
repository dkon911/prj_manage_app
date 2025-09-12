from utils.authen import _hash_password

pw = _hash_password("Admin123!")
print(f"this is pw after hash: {pw}")

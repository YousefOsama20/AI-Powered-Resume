import requests

BASE_URL = "http://localhost:8000/api"

print("--- Testing Customer Registration ---")
reg_res = requests.post(f"{BASE_URL}/auth/register", json={
    "email": "customer@example.com",
    "password": "securepassword",
    "role": "CUSTOMER",
    "name": "John Doe"
})
print("Register Response:", reg_res.status_code, reg_res.json())

print("\n--- Testing Company Registration ---")
comp_res = requests.post(f"{BASE_URL}/auth/register", json={
    "email": "company@example.com",
    "password": "securepassword",
    "role": "COMPANY",
    "name": "Tech Corp"
})
print("Register Response:", comp_res.status_code, comp_res.json())

print("\n--- Testing Login ---")
login_res = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "customer@example.com",
    "password": "securepassword"
})
print("Login Response:", login_res.status_code, login_res.json())

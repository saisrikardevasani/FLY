"""Plain asserts over the parts that need no Supabase round trip.

Run it with:  .venv/bin/python test_auth.py
"""

import main
from fastapi.testclient import TestClient

client = TestClient(main.app)
BAD_TOKEN = "eyJhbGciOiJIUzI1NiJ9.not.a.real.token"


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"  ok  {name}")


print("the server never stores a password")
source = open("main.py").read()
for forbidden in ("bcrypt", "hashlib", "passlib", "sha256"):
    check(f"no {forbidden} anywhere in the file", forbidden not in source)
check("the anon key is what is configured, not the service role",
      "service_role" not in source)

print("input validation, before any call to Supabase")
check("no password is a 400", client.post("/auth/signup", json={"email": "a@b.com"}).status_code == 400)
check("no email is a 400", client.post("/auth/signup", json={"password": "x"}).status_code == 400)
check("an empty password is a 400",
      client.post("/auth/signup", json={"email": "a@b.com", "password": ""}).status_code == 400)
check("a malformed email is a 400",
      client.post("/auth/signup", json={"email": "not-an-email", "password": "x"}).status_code == 400)
check("the error names the field",
      "password" in client.post("/auth/signup", json={"email": "a@b.com"}).json()["error"])
check("login validates the same way",
      client.post("/auth/login", json={"email": "a@b.com"}).status_code == 400)

print("the public lobby")
r = client.get("/public/info")
check("anyone may read it", r.status_code == 200)
check("it says what the brief asks it to say",
      r.json() == {"message": "Welcome stranger! This info is public."})

print("the locked doors, without a token")
for route in ("/protected/profile", "/protected/dashboard"):
    r = client.get(route)
    check(f"{route} with no header is a 401", r.status_code == 401)
    check(f"{route} says a token is required", r.json() == {"error": "Access token required"})

r = client.post("/auth/logout")
check("/auth/logout is protected too", r.status_code == 401)

print("malformed Authorization headers are all refused the same way")
for header in ("Bearer", "Bearer ", "sometoken", "Basic abc123", ""):
    code = client.get("/protected/profile", headers={"Authorization": header}).status_code
    check(f"{header!r} is a 401", code == 401)

print("a well-formed but forged token reaches Supabase and is rejected")
r = client.get("/protected/profile", headers={"Authorization": f"Bearer {BAD_TOKEN}"})
check("a forged token is a 401", r.status_code == 401)
check("and the message says why", r.json() == {"error": "Invalid or expired token"})

print("swagger advertises the padlock")
schema = client.get("/openapi.json").json()
schemes = schema["components"]["securitySchemes"]
check("a bearer scheme is declared", any(
    s.get("scheme") == "bearer" and s.get("type") == "http" for s in schemes.values()))
for route in ("/protected/profile", "/protected/dashboard", "/auth/logout"):
    method = "post" if route == "/auth/logout" else "get"
    check(f"{route} is marked as needing it",
          "security" in schema["paths"][route][method])
for route in ("/public/info", "/auth/login"):
    method = "post" if route == "/auth/login" else "get"
    check(f"{route} is not", "security" not in schema["paths"][route][method])

print("\nall checks passed")

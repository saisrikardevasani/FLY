# Prompt v1

Written from memory before generating anything, without re-reading the assignment brief. The
generated code goes in this folder and is never edited afterwards.

---

Build me a FastAPI service where Supabase is the identity provider and my server only verifies
the tokens it issues. I am using the Python `supabase` client and the project's **anon** key,
loaded from `.env` with `python-dotenv`. My server must never store a password and must never
hash anything itself.

Five routes:

- `POST /auth/signup` takes JSON with `email` and `password`. Call Supabase's sign up method. If
  either field is missing, return `400` with a JSON error. On success return `201` with the user.
- `POST /auth/login` takes the same body and calls sign in with password. Missing fields are
  `400`. If Supabase rejects the credentials, return `401` with
  `{"error": "Invalid login credentials"}`. On success return `200` with the access token and the
  refresh token that Supabase gives back.
- `POST /auth/logout` is protected. Call Supabase's sign out and return `204`.
- `GET /public/info` needs no auth and returns
  `{"message": "Welcome stranger! This info is public."}` with `200`.
- `GET /protected/profile` is protected and returns the user's id, email and account creation
  date.

For the protected routes, the client sends `Authorization: Bearer <token>`. Pull the token out of
that header and ask Supabase whether it is real, using its get user method with the token. If the
header is missing or there is no token, return `401` with `{"error": "Access token required"}`.
If Supabase says the token is expired, tampered with or otherwise invalid, return `401` with
`{"error": "Invalid or expired token"}`.

Do not paste the token check into each route. Put it in one reusable dependency so that adding a
protected route needs no new auth code, and add a second protected route
`GET /protected/dashboard` to show that it works.

Finally, make Swagger show a padlock on the protected routes and give me an Authorize button I
can paste a token into, so I can call `GET /protected/profile` from the browser without curl.

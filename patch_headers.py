import sys

with open(r'backend\app\main.py', 'r') as f:
    text = f.read()

security_headers = '''@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    # We omit strict CSP here because the frontend usually handles it, but adding a basic one for API:
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

@app.middleware("http")
async def correlation_id_and_logging_middleware'''

text = text.replace('@app.middleware("http")\nasync def correlation_id_and_logging_middleware', security_headers)

with open(r'backend\app\main.py', 'w') as f:
    f.write(text)

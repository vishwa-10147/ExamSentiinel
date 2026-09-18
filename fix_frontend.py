import sys

with open(r'frontend\services\apiClient.ts', 'r', encoding='utf-8') as f:
    text = f.read()

old_headers = '''    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    const token = this.getAccessToken();
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    
    // Do not set Content-Type to application/json for FormData
    if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.method !== "GET") {
        headers.set("Content-Type", "application/json");
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });'''

new_headers = '''    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    const token = this.getAccessToken();
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Do not set Content-Type to application/json for FormData
    if (!(options.body instanceof FormData) && !headers["Content-Type"] && options.method !== "GET") {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });'''

if old_headers in text:
    text = text.replace(old_headers, new_headers)
else:
    print("COULD NOT FIND HEADERS BLOCK")

with open(r'frontend\services\apiClient.ts', 'w', encoding='utf-8') as f:
    f.write(text)

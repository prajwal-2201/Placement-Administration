with open('api/index.py', 'a') as f:
    f.write('\nfrom fastapi import Request\n@app.route("/{path:path}", methods=["GET", "POST"])\nasync def catch_all(request: Request, path: str):\n    return {"caught_path": path, "url": str(request.url)}\n')

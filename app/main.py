from fastapi import FastAPI

app = FastAPI(title="My FastAPI Application", version="0.1.0")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the API"}

from app.routers import users
from app.routers import organisations as org_router
from app.routers import roles as roles_router

app.include_router(users.router)
app.include_router(org_router.router)
app.include_router(roles_router.router)

# Placeholder for future routers
# from app.routers import items (example)
# app.include_router(items.router)

from fastapi import FastAPI
from app.routes import auth,get_api,projects

app = FastAPI()

app.include_router(auth.router)
app.include_router(get_api.router)
app.include_router(projects.router)

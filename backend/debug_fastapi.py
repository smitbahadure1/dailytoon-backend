from fastapi import FastAPI, APIRouter
import fastapi
print(f"FastAPI version: {fastapi.__version__}")
print(f"APIRouter: {APIRouter}")
try:
    router = APIRouter()
    print("Router created successfully")
except Exception as e:
    print(f"Error creating router: {e}")

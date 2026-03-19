from fastapi import FastAPI

app = FastAPI(title="Gmail Discount Tracker API")


@app.get("/")
def root():
    return {"message": "Gmail Discount Tracker API is running"}

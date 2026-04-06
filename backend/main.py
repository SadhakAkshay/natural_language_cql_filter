from fastapi import FastAPI
from table_attribute import router
from dynamic_cql_filter_api import language

app = FastAPI(
    title="NLP GIS API",
    description="Backend for Natural Language GIS Application",
    version="1.0.0"
)

# Include routers
app.include_router(router, prefix="/api")
app.include_router(language, prefix="/api")


@app.get("/")
def root():
    return {"message": "NLP GIS Backend Running Successfully 🚀"}
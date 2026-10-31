from fastapi import FastAPI

app = FastAPI(title="Catalog MCP Server")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

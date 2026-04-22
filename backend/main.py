import uvicorn
import time
start = time.time()

from core.config import get_settings

def main():
    settings = get_settings()
    print(f"Config loaded: {time.time() - start:.2f}s")

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    print(f"Imports complete: {time.time() - start:.2f}s")
    main()
"""
Wrapper para ejecutar uvicorn con ProactorEventLoop en Windows.
Necesario porque Playwright async requiere subprocess support.
"""
import asyncio
import logging
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True, loop="asyncio")

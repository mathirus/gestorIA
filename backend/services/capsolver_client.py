"""
Cliente async de CapSolver para resolver captchas automaticamente.
Soporta: reCAPTCHA v2, reCAPTCHA Enterprise, Cloudflare Turnstile, Image captcha.
"""

import asyncio
import aiohttp
from config import settings

CREATE_TASK_URL = "https://api.capsolver.com/createTask"
GET_RESULT_URL = "https://api.capsolver.com/getTaskResult"


async def create_task(session: aiohttp.ClientSession, task: dict) -> str:
    payload = {"clientKey": settings.capsolver_api_key, "task": task}
    async with session.post(CREATE_TASK_URL, json=payload) as resp:
        data = await resp.json()
    if data.get("errorId") != 0:
        raise RuntimeError(f"CapSolver createTask failed: {data.get('errorCode')} - {data.get('errorDescription')}")
    return data["taskId"]


async def get_result(session: aiohttp.ClientSession, task_id: str, timeout: int = 120) -> dict:
    payload = {"clientKey": settings.capsolver_api_key, "taskId": task_id}
    elapsed = 0
    await asyncio.sleep(3)
    while elapsed < timeout:
        async with session.post(GET_RESULT_URL, json=payload) as resp:
            data = await resp.json()
        if data.get("errorId") != 0:
            raise RuntimeError(f"CapSolver error: {data.get('errorCode')} - {data.get('errorDescription')}")
        if data["status"] == "ready":
            return data["solution"]
        if data["status"] == "failed":
            raise RuntimeError(f"CapSolver task failed: {data}")
        await asyncio.sleep(3)
        elapsed += 3
    raise TimeoutError(f"CapSolver task {task_id} timed out after {timeout}s")


async def solve(task: dict) -> dict:
    """Crea tarea y espera resultado. Maneja su propia session."""
    async with aiohttp.ClientSession() as session:
        task_id = await create_task(session, task)
        return await get_result(session, task_id)

from verification.support import load
import pytest

def module():
    return load('world2/level_2_4_other.py')

def test_async():
    import asyncio
    from fastapi import HTTPException
    async def ok(): return 18.5
    assert asyncio.run(module().fetch_forecast(ok))=={"temperature":18.5}
    async def timeout(): raise TimeoutError()
    with pytest.raises(HTTPException) as e: asyncio.run(module().fetch_forecast(timeout))
    assert e.value.status_code==503
    assert e.value.detail=="Weather service unavailable"
    async def bug(): raise ValueError("bug")
    with pytest.raises(ValueError): asyncio.run(module().fetch_forecast(bug))

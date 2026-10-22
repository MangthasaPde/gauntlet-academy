from verification.support import load
import pytest

def module():
    return load('world2/level_2_4_biology.py')

def test_async():
    import asyncio
    from fastapi import HTTPException
    async def ok(): return 3.3
    assert asyncio.run(module().fetch_reading(ok))=={"reading":3.3}
    async def timeout(): raise TimeoutError()
    with pytest.raises(HTTPException) as e: asyncio.run(module().fetch_reading(timeout))
    assert e.value.status_code==503
    assert e.value.detail=="Instrument unavailable"
    async def bug(): raise ValueError("bug")
    with pytest.raises(ValueError): asyncio.run(module().fetch_reading(bug))

from verification.support import load
import pytest

def module():
    return load('world2/level_2_4_business.py')

def test_async():
    import asyncio
    from fastapi import HTTPException
    async def ok(): return 1.08
    assert asyncio.run(module().fetch_exchange_rate(ok))=={"rate":1.08}
    async def timeout(): raise TimeoutError()
    with pytest.raises(HTTPException) as e: asyncio.run(module().fetch_exchange_rate(timeout))
    assert e.value.status_code==503
    assert e.value.detail=="Rate service unavailable"
    async def bug(): raise ValueError("bug")
    with pytest.raises(ValueError): asyncio.run(module().fetch_exchange_rate(bug))

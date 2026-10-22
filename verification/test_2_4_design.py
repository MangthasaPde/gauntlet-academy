from verification.support import load
import pytest

def module():
    return load('world2/level_2_4_design.py')

def test_async():
    import asyncio
    from fastapi import HTTPException
    async def ok(): return 0.75
    assert asyncio.run(module().fetch_progress(ok))=={"progress":0.75}
    async def timeout(): raise TimeoutError()
    with pytest.raises(HTTPException) as e: asyncio.run(module().fetch_progress(timeout))
    assert e.value.status_code==503
    assert e.value.detail=="Render service unavailable"
    async def bug(): raise ValueError("bug")
    with pytest.raises(ValueError): asyncio.run(module().fetch_progress(bug))

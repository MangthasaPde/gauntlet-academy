"""Best-effort resource limits for accidental runaway student code, not isolation."""
import sys
try:
    import resource  # Unix only; on Windows the 45 second timeout in main.py is the only limit.
    resource.setrlimit(resource.RLIMIT_CPU,(35,35))
    resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024*1024,4*1024*1024))
except ImportError:
    pass
import pytest
raise SystemExit(pytest.main([sys.argv[1],'-q','--tb=short','--color=no','-p','no:cacheprovider']))

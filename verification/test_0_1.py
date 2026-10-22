from verification.support import load
import pytest

def module():
    return load('world0/level_0_1.py')

@pytest.mark.parametrize("name,want", [("Ada","Hello, Ada!"),("  Sam ","Hello, Sam!"),("Mei Ling","Hello, Mei Ling!")])
def test_greets_by_name(name,want):
    assert module().greet(name)==want

@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name(name):
    assert module().greet(name)=="Hello, friend!"

from verification.support import load
import pytest

def module():
    return load('world1/level_1_1_business.py')

@pytest.mark.parametrize("invoice,amount,paid,want", [("INV-1001",1234.5,True,"INV-1001 | 1234.50 USD | PAID"),("INV-0",0,False,"INV-0 | 0.00 USD | UNPAID"),("CR-7",-45.678,True,"CR-7 | -45.68 USD | PAID"),("INV-9",99.999,False,"INV-9 | 100.00 USD | UNPAID")])
def test_invoice_line(invoice,amount,paid,want):
    assert module().format_invoice(invoice,amount,paid)==want

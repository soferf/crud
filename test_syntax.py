#!/usr/bin/env python3
import sys
import py_compile

try:
    py_compile.compile(r'C:\DIPLOMADO\crud\app.py', doraise=True)
    print("✓ SYNTAX OK - No syntax errors found in app.py")
    sys.exit(0)
except py_compile.PyCompileError as e:
    print("✗ SYNTAX ERROR - Errors found in app.py:")
    print(e)
    sys.exit(1)

"""Permite ejecutar AudioRep como módulo: python -m audiorep"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from main import main as _main
    _main()


if __name__ == "__main__":
    main()

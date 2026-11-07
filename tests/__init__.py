"""Тесты приложения; добавляют папку src в путь поиска модулей."""
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(os.path.dirname(TESTS_DIR), "src")
sys.path.insert(0, SRC_DIR)

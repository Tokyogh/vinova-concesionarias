#!/usr/bin/env python
"""ES: Punto de entrada de línea de comandos para administrar el proyecto Django.

EN: Command-line entry point for Django project administration.
"""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

"""Punto de entrada del sistema. Ejecutar con: python main.py"""

from pathlib import Path

from src.application import Application
from src.cli import run
from src.storage import StorageError


def main():
    """Inicia la aplicación y muestra errores de inicio de forma clara."""
    try:
        # Usar rutas absolutas basadas en este archivo permite ejecutar desde otra carpeta.
        app = Application(Path(__file__).resolve().parent / "data")
        run(app)
    except StorageError as error:
        print("No fue posible iniciar el sistema:", error)
    except (KeyboardInterrupt, EOFError):
        print("\nPrograma cerrado. Los cambios confirmados quedaron guardados.")


main()

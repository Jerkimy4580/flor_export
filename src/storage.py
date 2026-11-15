"""Persistencia en TXT usando JSON de la biblioteca estándar de Python."""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


class StorageError(Exception):
    """Error recuperable de lectura o guardado de los datos."""


class TextStorage:
    """Lee y guarda la base de datos y sus copias de seguridad."""

    def __init__(self, data_dir):
        """Prepara las rutas de datos y crea las carpetas necesarias."""
        self.data_dir = Path(data_dir)
        self.file = self.data_dir / "database.txt"
        self.backups = self.data_dir / "backups"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backups.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _read_file(path):
        """Lee y valida un archivo de datos JSON."""
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict) or data.get("schema_version") != 1:
                raise StorageError("Archivo de datos con formato incompatible.")
            for key in ("flowers", "orders", "bouquets", "next_id", "undo", "redo", "audit"):
                if key not in data:
                    raise StorageError(f"Al archivo de datos le falta '{key}'.")
            for key in ("flowers", "orders", "bouquets", "undo", "redo", "audit"):
                if not isinstance(data[key], list):
                    raise StorageError(f"La sección '{key}' tiene un formato inválido.")
            if (isinstance(data["next_id"], bool) or
                    not isinstance(data["next_id"], int) or data["next_id"] < 1):
                raise StorageError("El siguiente identificador no es válido.")
            return data
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise StorageError(f"No se pudo leer el archivo TXT: {error}") from error

    def load(self):
        """Carga la base principal o indica que todavía no existe."""
        if not self.file.exists():
            return None
        return self._read_file(self.file)

    def save(self, data):
        """Escribe primero a un temporal y reemplaza de forma atómica."""
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.data_dir,
                prefix="database_", suffix=".tmp", delete=False
            ) as handle:
                temporary_name = handle.name
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.file)
        except (OSError, TypeError, ValueError) as error:
            raise StorageError(f"No se pudo guardar el TXT: {error}") from error
        finally:
            if temporary_name and os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def create_backup(self):
        """Crea una copia del archivo principal con nombre único."""
        if not self.file.exists():
            raise StorageError("Todavía no existe la base de datos.")
        name = "respaldo_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".txt"
        destination = self.backups / name
        temporary = self.backups / (name + ".tmp")
        try:
            shutil.copy2(self.file, temporary)
            os.replace(temporary, destination)
        except OSError as error:
            raise StorageError(f"No se pudo crear el respaldo: {error}") from error
        finally:
            if temporary.exists():
                temporary.unlink()
        return name

    def list_backups(self):
        """Lista los respaldos disponibles del más reciente al más antiguo."""
        return sorted((path.name for path in self.backups.glob("respaldo_*.txt")), reverse=True)

    def read_backup(self, name):
        """Lee un respaldo existente y valida su contenido."""
        if name not in self.list_backups():
            raise ValueError("Ese respaldo no existe en la carpeta de copias.")
        return self._read_file(self.backups / name)

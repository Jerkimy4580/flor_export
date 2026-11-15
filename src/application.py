"""Coordinador de servicios y transacciones del sistema."""

from copy import deepcopy

from .models import Bouquet, Flower, Order, now_text
from .storage import StorageError, TextStorage
from .structures import LinkedList, Stack


class Application:
    """Comparte modelos y guardado entre los tres módulos del negocio."""

    HISTORY_LIMIT = 30

    def __init__(self, data_dir):
        """Carga o crea los datos y conecta los servicios del sistema."""
        self.storage = TextStorage(data_dir)
        saved = self.storage.load()
        if saved is None:
            self._load_full(self._initial_data())
            self.storage.save(self.to_dict())
        else:
            try:
                self._load_full(saved)
            except (KeyError, TypeError, ValueError) as error:
                raise StorageError(f"Los registros del TXT están dañados: {error}") from error

        # Importaciones aquí para evitar dependencias circulares.
        from .services.inventory import InventoryService
        from .services.orders import OrderService
        from .services.shipping import ShippingService
        from .services.catalog import CatalogService

        self.inventory = InventoryService(self)
        self.orders_service = OrderService(self)
        self.shipping = ShippingService(self)
        self.catalog = CatalogService(self)

    @staticmethod
    def _initial_data():
        """Catálogo ilustrativo, editable desde el menú."""
        flowers = [
            Flower("R01", "Rosa", "Rojo", 80, 150, 15),
            Flower("R02", "Rosa", "Blanco", 60, 140, 10),
            Flower("G01", "Girasol", "Amarillo", 50, 200, 10),
            Flower("T01", "Tulipán", "Rosado", 35, 230, 8),
            Flower("L01", "Lirio", "Blanco", 45, 220, 8),
            Flower("M01", "Margarita", "Blanco", 100, 90, 20),
        ]
        bouquets = [
            Bouquet("C01", "Romántico", "pequeno", [
                {"flower_id": "R01", "quantity": 4},
                {"flower_id": "R02", "quantity": 2},
            ]),
            Bouquet("C02", "Primavera", "mediano", [
                {"flower_id": "G01", "quantity": 5},
                {"flower_id": "M01", "quantity": 4},
            ]),
            Bouquet("C03", "Elegante", "grande", [
                {"flower_id": "T01", "quantity": 8},
                {"flower_id": "L01", "quantity": 6},
            ]),
        ]
        return {
            "schema_version": 1,
            "flowers": [item.to_dict() for item in flowers],
            "orders": [],
            "bouquets": [item.to_dict() for item in bouquets],
            "next_id": 1,
            "undo": [], "redo": [], "audit": [],
        }

    def _load_full(self, data):
        """Restaura todos los datos guardados, incluido el historial."""
        self.flowers = LinkedList(Flower(**item) for item in data["flowers"])
        self.orders = LinkedList(Order.from_dict(item) for item in data["orders"])
        self.bouquets = LinkedList(Bouquet(**item) for item in data["bouquets"])
        self.next_id = int(data["next_id"])
        self.undo_stack = Stack(deepcopy(data["undo"]))
        self.redo_stack = Stack(deepcopy(data["redo"]))
        self.audit = deepcopy(data["audit"])

    def business_data(self):
        """Datos que se restauran al usar deshacer o rehacer."""
        return {
            "flowers": [item.to_dict() for item in self.flowers],
            "orders": [item.to_dict() for item in self.orders],
            "bouquets": [item.to_dict() for item in self.bouquets],
            "next_id": self.next_id,
        }

    def to_dict(self):
        """Prepara el estado completo para guardarlo en el archivo."""
        return {
            "schema_version": 1,
            **self.business_data(),
            "undo": self.undo_stack.to_list(),
            "redo": self.redo_stack.to_list(),
            "audit": deepcopy(self.audit),
        }

    def _set_business(self, snapshot):
        """Restaura datos del negocio sin reutilizar identificadores."""
        self.flowers = LinkedList(Flower(**item) for item in snapshot["flowers"])
        self.orders = LinkedList(Order.from_dict(item) for item in snapshot["orders"])
        self.bouquets = LinkedList(Bouquet(**item) for item in snapshot["bouquets"])
        # Los códigos ya asignados nunca se reutilizan al deshacer.
        self.next_id = max(self.next_id, snapshot["next_id"])

    def _record(self, message):
        """Añade una operación al historial y conserva solo las últimas cien."""
        self.audit.append({"at": now_text(), "message": message})
        self.audit = self.audit[-100:]

    def _limit_stack(self, stack):
        """Limita la pila de cambios a los estados más recientes."""
        return Stack(stack.to_list()[-self.HISTORY_LIMIT:])

    def change(self, message, action):
        """Actualiza memoria + TXT como una unidad; revierte ante errores."""
        old_full = deepcopy(self.to_dict())
        try:
            result = action()
            self.undo_stack.push(self._business_from_full(old_full))
            self.undo_stack = self._limit_stack(self.undo_stack)
            self.redo_stack = Stack()
            self._record(message)
            self.storage.save(self.to_dict())
            return result
        except Exception:
            self._load_full(old_full)
            raise

    @staticmethod
    def _business_from_full(data):
        """Extrae los datos del negocio de una instantánea completa."""
        return {key: deepcopy(data[key]) for key in ("flowers", "orders", "bouquets", "next_id")}

    def undo(self):
        """Restaura el estado anterior y conserva el actual para rehacerlo."""
        if not len(self.undo_stack):
            raise ValueError("No hay operaciones para deshacer.")
        old_full = deepcopy(self.to_dict())
        try:
            previous = self.undo_stack.pop()
            self.redo_stack.push(self.business_data())
            self.redo_stack = self._limit_stack(self.redo_stack)
            self._set_business(previous)
            self._record("Se deshizo la última operación")
            self.storage.save(self.to_dict())
        except Exception:
            self._load_full(old_full)
            raise

    def redo(self):
        """Restaura el siguiente estado guardado en la pila de rehacer."""
        if not len(self.redo_stack):
            raise ValueError("No hay operaciones para rehacer.")
        old_full = deepcopy(self.to_dict())
        try:
            next_state = self.redo_stack.pop()
            self.undo_stack.push(self.business_data())
            self.undo_stack = self._limit_stack(self.undo_stack)
            self._set_business(next_state)
            self._record("Se rehízo la última operación")
            self.storage.save(self.to_dict())
        except Exception:
            self._load_full(old_full)
            raise

    def create_backup(self):
        """Solicita al almacenamiento una copia de seguridad."""
        return self.storage.create_backup()

    def restore_backup(self, name):
        """Copia el estado actual antes de restaurar un respaldo elegido."""
        restored = self.storage.read_backup(name)
        current = deepcopy(self.to_dict())
        preventive_backup = self.storage.create_backup()
        try:
            self._load_full(restored)
            self.storage.save(self.to_dict())
        except Exception as error:
            self._load_full(current)
            if isinstance(error, (KeyError, TypeError, ValueError)):
                raise StorageError(f"El respaldo no contiene registros válidos: {error}") from error
            raise
        return preventive_backup

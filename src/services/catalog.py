"""Administración de ramilletes existentes en el catálogo."""

from ..models import Bouquet, SIZE_RULES, positive_int, required


class CatalogService:
    """Valida y administra los ramilletes prediseñados."""

    def __init__(self, app):
        """Conecta las operaciones del catálogo con la aplicación."""
        self.app = app

    def get(self, bouquet_id):
        """Busca un ramillete del catálogo por código."""
        return self.app.bouquets.find(lambda item: item.id == bouquet_id.strip().upper())

    def list_all(self):
        """Devuelve todos los ramilletes registrados."""
        return list(self.app.bouquets)

    def _validate(self, name, size, items):
        """Valida composición y tamaño, agrupando flores repetidas."""
        name = required(name, "nombre del ramillete")
        if size not in SIZE_RULES:
            raise ValueError("Tamaño incorrecto.")
        quantities = {}
        for flower_id, quantity in items:
            flower_id = required(flower_id, "código de flor").upper()
            if not self.app.inventory.get(flower_id):
                raise ValueError(f"La flor {flower_id} no existe.")
            quantities[flower_id] = quantities.get(flower_id, 0) + positive_int(quantity, "Cantidad")
        lower, upper, _ = SIZE_RULES[size]
        if not lower <= sum(quantities.values()) <= upper:
            raise ValueError(f"El tamaño {size} requiere entre {lower} y {upper} flores.")
        return name, [{"flower_id": key, "quantity": value} for key, value in quantities.items()]

    def add(self, bouquet_id, name, size, items):
        """Valida y agrega un ramillete nuevo al catálogo."""
        bouquet_id = required(bouquet_id, "código del catálogo").upper()
        if self.get(bouquet_id):
            raise ValueError("Ya existe ese código de ramillete.")
        name, lines = self._validate(name, size, items)
        return self.app.change(f"Ramillete agregado {bouquet_id}",
                               lambda: self.app.bouquets.append(Bouquet(bouquet_id, name, size, lines)))

    def edit(self, bouquet_id, name, size, items):
        """Reemplaza los datos de un ramillete existente."""
        bouquet = self.get(bouquet_id)
        if not bouquet:
            raise ValueError("El ramillete no existe.")
        name, lines = self._validate(name, size, items)

        def apply():
            """Guarda los campos editados después de validarlos."""
            bouquet.name, bouquet.size, bouquet.items = name, size, lines

        return self.app.change(f"Ramillete modificado {bouquet.id}", apply)

    def remove(self, bouquet_id):
        """Elimina un ramillete existente del catálogo."""
        bouquet = self.get(bouquet_id)
        if not bouquet:
            raise ValueError("El ramillete no existe.")
        return self.app.change(f"Ramillete eliminado {bouquet.id}",
                               lambda: self.app.bouquets.remove(lambda b: b.id == bouquet.id))

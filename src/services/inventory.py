"""Reglas del inventario y alertas por existencias bajas."""

from ..models import Flower, positive_int, required


class InventoryService:
    """Valida y ejecuta cambios en las flores y sus existencias."""

    def __init__(self, app):
        """Conecta las operaciones de inventario con la aplicación."""
        self.app = app

    def get(self, flower_id):
        """Busca una flor por código, sin distinguir mayúsculas."""
        return self.app.flowers.find(lambda flower: flower.id == flower_id.strip().upper())

    def list_all(self):
        """Devuelve todas las flores registradas."""
        return list(self.app.flowers)

    def low_stock(self):
        """Devuelve las flores que llegaron a su mínimo o están por debajo."""
        return [flower for flower in self.app.flowers if flower.stock <= flower.minimum]

    def add(self, flower_id, name, color, quantity, price_cents, minimum):
        """Valida y registra una nueva variedad de flor."""
        flower_id = required(flower_id, "código").upper()
        name = required(name, "nombre")
        color = required(color, "color")
        quantity = positive_int(quantity, "Stock", allow_zero=True)
        minimum = positive_int(minimum, "Mínimo", allow_zero=True)
        price_cents = positive_int(price_cents, "Precio en centavos", allow_zero=True)
        if self.get(flower_id):
            raise ValueError("Ya existe una flor con ese código.")
        if any(f.name.casefold() == name.casefold() and f.color.casefold() == color.casefold()
               for f in self.app.flowers):
            raise ValueError("Ya existe una flor con ese nombre y color.")
        return self.app.change(f"Flor agregada {flower_id}", lambda: self.app.flowers.append(
            Flower(flower_id, name, color, quantity, price_cents, minimum)))

    def restock(self, flower_id, quantity):
        """Suma al inventario las unidades recibidas."""
        flower = self.get(flower_id)
        if not flower:
            raise ValueError("La flor no existe.")
        quantity = positive_int(quantity, "Cantidad del lote")
        return self.app.change(f"Reposición de {quantity} unidades de {flower.id}",
                               lambda: setattr(flower, "stock", flower.stock + quantity))

    def edit(self, flower_id, name, color, price_cents, minimum):
        """Actualiza los datos comerciales de una flor existente."""
        flower = self.get(flower_id)
        if not flower:
            raise ValueError("La flor no existe.")
        name, color = required(name, "nombre"), required(color, "color")
        price_cents = positive_int(price_cents, "Precio", allow_zero=True)
        minimum = positive_int(minimum, "Mínimo", allow_zero=True)
        if any(f.id != flower.id and f.name.casefold() == name.casefold()
               and f.color.casefold() == color.casefold() for f in self.app.flowers):
            raise ValueError("Ese nombre y color ya están registrados.")

        def apply():
            """Aplica los cambios después de validar los datos."""
            flower.name, flower.color = name, color
            flower.price_cents, flower.minimum = price_cents, minimum

        return self.app.change(f"Flor modificada {flower.id}", apply)

    def remove(self, flower_id):
        """Elimina una flor solo si ningún registro activo la utiliza."""
        flower = self.get(flower_id)
        if not flower:
            raise ValueError("La flor no existe.")
        if any(item["flower_id"] == flower.id for template in self.app.bouquets for item in template.items):
            raise ValueError("La flor está en un ramillete del catálogo. Retírela primero de él.")
        if any(item.flower_id == flower.id for order in self.app.orders
               for item in order.items if order.status != "cancelado"):
            raise ValueError("La flor figura en pedidos registrados; no se puede eliminar.")
        return self.app.change(f"Flor eliminada {flower.id}",
                               lambda: self.app.flowers.remove(lambda f: f.id == flower.id))

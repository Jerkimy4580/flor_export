"""Pedidos, personalización de ramilletes y actualización de stock."""

from ..models import (
    Order, OrderItem, SIZE_RULES, calculate_tax, now_text, positive_int, required,
)


class OrderService:
    """Valida pedidos y coordina sus precios y existencias."""

    def __init__(self, app):
        """Conecta la gestión de pedidos con inventario y almacenamiento."""
        self.app = app

    def get(self, order_id):
        """Busca un pedido por su identificador."""
        return self.app.orders.find(lambda item: item.id == order_id.strip().upper())

    def list_all(self):
        """Devuelve todos los pedidos registrados."""
        return list(self.app.orders)

    def preview(self, customer, phone, country, address, size, priority, items,
                bouquet_name="Personalizado", order_id=None):
        """Calcula y valida la compra sin modificar el inventario."""
        customer, country, address = (required(customer, "cliente"),
                                      required(country, "país"), required(address, "dirección"))
        phone = required(phone, "teléfono")
        if len(phone) != 10 or not phone.isdigit():
            raise ValueError("El teléfono debe tener exactamente 10 dígitos.")
        if size not in SIZE_RULES:
            raise ValueError("Seleccione un tamaño válido.")
        priority = positive_int(priority, "Prioridad")
        if priority not in (1, 2, 3):
            raise ValueError("La prioridad debe ser 1, 2 o 3.")
        bouquet_name = required(bouquet_name, "nombre del ramillete")

        old_order = self.get(order_id) if order_id else None
        if order_id and not old_order:
            raise ValueError("El pedido que desea editar no existe.")
        old_quantities = {}
        if old_order:
            for item in old_order.items:
                old_quantities[item.flower_id] = item.quantity

        # Agrupar códigos repetidos evita descontar stock incorrectamente.
        quantities = {}
        for flower_id, quantity in items:
            flower_id = required(flower_id, "código de flor").upper()
            quantity = positive_int(quantity, "Cantidad")
            quantities[flower_id] = quantities.get(flower_id, 0) + quantity

        flower_count = sum(quantities.values())
        lower, upper, packaging = SIZE_RULES[size]
        if not lower <= flower_count <= upper:
            raise ValueError(f"Un ramillete {size} requiere entre {lower} y {upper} flores.")

        selected = []
        for flower_id, quantity in quantities.items():
            flower = self.app.inventory.get(flower_id)
            if not flower:
                raise ValueError(f"La flor {flower_id} no existe.")
            available = flower.stock + old_quantities.get(flower_id, 0)
            if available < quantity:
                raise ValueError(f"Stock insuficiente para {flower.name} {flower.color}: "
                                 f"disponibles {available}, solicitadas {quantity}.")
            selected.append(OrderItem(flower.id, flower.name, flower.color,
                                      quantity, flower.price_cents))

        subtotal = sum(item.quantity * item.price_cents for item in selected)
        tax = calculate_tax(subtotal + packaging)
        current_time = now_text()
        return Order(
            id=old_order.id if old_order else f"P{self.app.next_id:05d}",
            customer=customer, phone=phone, country=country, address=address,
            bouquet_name=bouquet_name, size=size, items=selected,
            priority=priority, status=old_order.status if old_order else "pendiente",
            created_seq=old_order.created_seq if old_order else self.app.next_id,
            created_at=old_order.created_at if old_order else current_time,
            updated_at=current_time, subtotal_cents=subtotal, packaging_cents=packaging,
            tax_cents=tax, total_cents=subtotal + packaging + tax,
            tracking_code=old_order.tracking_code if old_order else "",
            events=list(old_order.events) if old_order else [],
        )

    def create(self, **details):
        """Crea un pedido confirmado y reserva las flores de su inventario."""
        # Volver a calcular al confirmar garantiza que no se use un precio antiguo.
        order = self.preview(**details)

        def apply():
            """Descuenta las flores y agrega el pedido al registro."""
            for item in order.items:
                self.app.inventory.get(item.flower_id).stock -= item.quantity
            order.events.append({"at": now_text(), "status": "pendiente"})
            self.app.orders.append(order)
            self.app.next_id += 1
            return order

        return self.app.change(f"Pedido creado {order.id}", apply)

    def edit(self, order_id, **details):
        """Actualiza un pedido pendiente y reajusta las existencias."""
        original = self.get(order_id)
        if not original:
            raise ValueError("El pedido no existe.")
        if original.status != "pendiente":
            raise ValueError("Solo puede editar pedidos pendientes.")
        modified = self.preview(order_id=original.id, **details)

        def apply():
            """Devuelve las flores anteriores y reserva la nueva composición."""
            # Se restaura el lote anterior y se reserva el nuevo en una transacción.
            for item in original.items:
                self.app.inventory.get(item.flower_id).stock += item.quantity
            for item in modified.items:
                self.app.inventory.get(item.flower_id).stock -= item.quantity
            modified.events.append({"at": now_text(), "status": "pedido_modificado"})
            original.__dict__.update(modified.__dict__)
            return original

        return self.app.change(f"Pedido editado {order_id}", apply)

    def cancel(self, order_id):
        """Cancela un pedido permitido y devuelve sus flores al inventario."""
        order = self.get(order_id)
        if not order:
            raise ValueError("El pedido no existe.")
        if order.status not in ("pendiente", "en_preparacion"):
            raise ValueError("Solo se pueden cancelar pedidos pendientes o en preparación.")

        def apply():
            """Actualiza estado e inventario en una sola operación."""
            for item in order.items:
                self.app.inventory.get(item.flower_id).stock += item.quantity
            order.status, order.updated_at = "cancelado", now_text()
            order.events.append({"at": now_text(), "status": "cancelado"})
            return order

        return self.app.change(f"Pedido cancelado {order_id}; stock devuelto", apply)

    def delete(self, order_id):
        """Elimina un pedido permitido y libera sus existencias reservadas."""
        order = self.get(order_id)
        if not order:
            raise ValueError("El pedido no existe.")
        if order.status in ("enviado", "entregado"):
            raise ValueError("No se elimina un pedido despachado; debe conservar su trazabilidad.")

        def apply():
            """Devuelve existencias si el pedido aún no estaba cancelado."""
            if order.status != "cancelado":
                for item in order.items:
                    self.app.inventory.get(item.flower_id).stock += item.quantity
            return self.app.orders.remove(lambda item: item.id == order.id)

        return self.app.change(f"Pedido eliminado {order_id}", apply)

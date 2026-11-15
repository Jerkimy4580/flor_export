"""Preparación FIFO, despacho priorizado y seguimiento de entregas."""

from ..models import now_text
from ..structures import PriorityShippingQueue, Queue


class ShippingService:
    """Controla preparación, despacho y seguimiento de pedidos."""

    def __init__(self, app):
        """Conecta las operaciones logísticas con los pedidos."""
        self.app = app

    def pending_queue(self):
        """Construye la cola FIFO desde pedidos pendientes persistidos en TXT."""
        queue = Queue()
        for order in sorted(self.app.orders, key=lambda value: value.created_seq):
            if order.status == "pendiente":
                queue.enqueue(order)
        return queue

    def shipping_queue(self):
        """Las colas se reconstruyen desde TXT para evitar duplicados u olvidos."""
        return PriorityShippingQueue(self.app.orders)

    def prepare_next(self):
        """Pasa a preparación el siguiente pedido pendiente por llegada."""
        queue = self.pending_queue()
        if not len(queue):
            raise ValueError("No existen pedidos pendientes.")
        order = queue.dequeue()

        def apply():
            """Cambia el pedido a preparación y registra el evento."""
            order.status = "en_preparacion"
            order.updated_at = now_text()
            order.events.append({"at": now_text(), "status": "en_preparacion"})
            return order

        return self.app.change(f"Pedido en preparación {order.id}", apply)

    def ship_next(self):
        """Despacha el pedido preparado con mayor prioridad."""
        order = self.shipping_queue().next()
        if order is None:
            raise ValueError("No existen pedidos preparados para despachar.")

        def apply():
            """Marca el pedido como enviado y asigna su guía."""
            order.status = "enviado"
            order.tracking_code = f"EXP-{order.id}-{order.created_seq:04d}"
            order.updated_at = now_text()
            order.events.append({"at": now_text(), "status": "enviado"})
            return order

        return self.app.change(f"Pedido enviado {order.id} hacia {order.country}", apply)

    def mark_delivered(self, order_id):
        """Confirma la entrega de un pedido que ya fue enviado."""
        order = self.app.orders_service.get(order_id)
        if not order:
            raise ValueError("El pedido no existe.")
        if order.status != "enviado":
            raise ValueError("Solo un pedido enviado puede marcarse como entregado.")

        def apply():
            """Registra el estado y la fecha de entrega."""
            order.status = "entregado"
            order.updated_at = now_text()
            order.events.append({"at": now_text(), "status": "entregado"})
            return order

        return self.app.change(f"Entrega confirmada {order.id}", apply)

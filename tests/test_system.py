"""Pruebas reales con archivos TXT temporales y datos independientes."""

import tempfile
import unittest
from pathlib import Path

from src.application import Application
from src.models import calculate_tax, parse_price
from src.storage import StorageError
from src.structures import LinkedList, PriorityShippingQueue, Queue, Stack


class TestStructures(unittest.TestCase):
    """Comprueba el comportamiento de las estructuras enlazadas."""

    def test_linked_list_insert_find_remove(self):
        """Verifica inserción, búsqueda y eliminación en la lista."""
        values = LinkedList([1, 2, 3])
        self.assertEqual(values.find(lambda number: number == 2), 2)
        self.assertEqual(values.remove(lambda number: number == 2), 2)
        self.assertEqual(list(values), [1, 3])
        self.assertEqual(len(values), 2)

    def test_stack_lifo(self):
        """Verifica que la pila retire primero el último valor agregado."""
        stack = Stack(["primero", "último"])
        self.assertEqual(stack.peek(), "último")
        self.assertEqual(stack.pop(), "último")
        self.assertEqual(stack.to_list(), ["primero"])

    def test_queue_fifo(self):
        """Verifica que la cola retire primero el valor más antiguo."""
        queue = Queue()
        queue.enqueue(10)
        queue.enqueue(20)
        self.assertEqual(queue.dequeue(), 10)
        self.assertEqual(queue.dequeue(), 20)
        self.assertEqual(len(queue), 0)


class TestSystem(unittest.TestCase):
    """Prueba servicios, persistencia, pedidos y envíos con datos temporales."""

    def setUp(self):
        """Crea una aplicación aislada para cada prueba."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name)
        self.app = Application(self.path)

    def tearDown(self):
        """Elimina los archivos temporales usados por la prueba."""
        self.temp_dir.cleanup()

    def details(self, items=None, priority=2, customer="Jeremy"):
        """Genera datos válidos reutilizables para crear pedidos de prueba."""
        return {
            "customer": customer, "phone": "0987654321", "country": "Chile",
            "address": "Calle Central 123", "size": "pequeno", "priority": priority,
            "items": items if items is not None else [("R01", 4)],
            "bouquet_name": "Personalizado",
        }

    def test_initial_data_and_low_stock(self):
        """Comprueba los datos iniciales y la alerta de stock bajo."""
        self.assertEqual(len(self.app.inventory.list_all()), 6)
        self.assertEqual(len(self.app.catalog.list_all()), 3)
        self.app.inventory.add("N01", "Clavel", "Morado", 3, 110, 5)
        self.assertTrue(any(f.id == "N01" for f in self.app.inventory.low_stock()))

    def test_preview_does_not_change_stock(self):
        """Confirma que la vista previa no reserva existencias."""
        stock = self.app.inventory.get("R01").stock
        preview = self.app.orders_service.preview(**self.details())
        self.assertEqual(preview.id, "P00001")
        self.assertEqual(self.app.inventory.get("R01").stock, stock)
        self.assertEqual(len(self.app.orders_service.list_all()), 0)

    def test_order_pricing_and_inventory(self):
        """Verifica el total del pedido y el descuento de inventario."""
        order = self.app.orders_service.create(**self.details())
        self.assertEqual(order.subtotal_cents, 600)
        self.assertEqual(order.packaging_cents, 200)
        self.assertEqual(order.tax_cents, 120)
        self.assertEqual(order.total_cents, 920)
        self.assertEqual(self.app.inventory.get("R01").stock, 76)
        self.assertEqual(order.status, "pendiente")

    def test_invalid_phone_and_stock_leave_state_unchanged(self):
        """Confirma que datos inválidos no alteren pedidos ni existencias."""
        bad = self.details()
        bad["phone"] = "123"
        with self.assertRaises(ValueError):
            self.app.orders_service.create(**bad)
        with self.assertRaises(ValueError):
            self.app.orders_service.create(**self.details(items=[("R01", 90)]))
        self.assertEqual(len(self.app.orders_service.list_all()), 0)
        self.assertEqual(self.app.inventory.get("R01").stock, 80)

    def test_order_edit_recalculates_and_restores_difference(self):
        """Comprueba el recálculo del precio y el ajuste del inventario al editar."""
        order = self.app.orders_service.create(**self.details())
        self.app.orders_service.edit(order.id, **self.details(items=[("R01", 2), ("R02", 2)]))
        self.assertEqual(self.app.inventory.get("R01").stock, 78)
        self.assertEqual(self.app.inventory.get("R02").stock, 58)
        self.assertEqual(self.app.orders_service.get(order.id).subtotal_cents, 580)

    def test_cancel_returns_stock_and_prevents_double_return(self):
        """Verifica la devolución única de existencias al cancelar."""
        order = self.app.orders_service.create(**self.details())
        self.app.orders_service.cancel(order.id)
        self.assertEqual(self.app.inventory.get("R01").stock, 80)
        with self.assertRaises(ValueError):
            self.app.orders_service.cancel(order.id)
        self.app.orders_service.delete(order.id)
        self.assertEqual(self.app.inventory.get("R01").stock, 80)

    def test_delete_active_order_restores_stock(self):
        """Comprueba que eliminar un pedido activo libere sus flores."""
        order = self.app.orders_service.create(**self.details())
        self.app.orders_service.delete(order.id)
        self.assertEqual(self.app.inventory.get("R01").stock, 80)
        self.assertIsNone(self.app.orders_service.get(order.id))

    def test_shipping_fifo_and_priority(self):
        """Comprueba preparación FIFO y despacho por prioridad."""
        first = self.app.orders_service.create(**self.details(priority=3, customer="Ana"))
        second = self.app.orders_service.create(**self.details(priority=1, customer="Luis"))
        self.assertEqual(self.app.shipping.prepare_next().id, first.id)
        self.assertEqual(self.app.shipping.prepare_next().id, second.id)
        self.assertEqual(self.app.shipping.ship_next().id, second.id)
        self.assertEqual(self.app.shipping.ship_next().id, first.id)
        self.assertEqual(self.app.shipping.mark_delivered(second.id).status, "entregado")
        with self.assertRaises(ValueError):
            self.app.orders_service.delete(second.id)

    def test_shipping_fifo_on_same_priority(self):
        """Comprueba el orden de llegada entre pedidos con igual prioridad."""
        first = self.app.orders_service.create(**self.details(priority=1))
        second = self.app.orders_service.create(**self.details(priority=1))
        self.app.shipping.prepare_next()
        self.app.shipping.prepare_next()
        self.assertEqual(self.app.shipping.shipping_queue().ordered()[0].id, first.id)
        self.assertEqual(self.app.shipping.shipping_queue().ordered()[1].id, second.id)

    def test_persistence_reopen_txt(self):
        """Verifica que los datos guardados se recuperen al reiniciar."""
        order = self.app.orders_service.create(**self.details())
        restarted = Application(self.path)
        self.assertEqual(restarted.orders_service.get(order.id).customer, "Jeremy")
        self.assertEqual(restarted.inventory.get("R01").stock, 76)
        self.assertTrue((self.path / "database.txt").exists())

    def test_undo_redo_after_restart(self):
        """Verifica que deshacer y rehacer sobrevivan al reinicio."""
        self.app.orders_service.create(**self.details())
        self.app.undo()
        self.assertEqual(len(self.app.orders_service.list_all()), 0)
        self.assertEqual(self.app.inventory.get("R01").stock, 80)
        restarted = Application(self.path)
        restarted.redo()
        self.assertEqual(len(restarted.orders_service.list_all()), 1)
        self.assertEqual(restarted.inventory.get("R01").stock, 76)

    def test_order_id_is_not_reused_after_undo(self):
        """Evita reutilizar un identificador de pedido deshecho."""
        first = self.app.orders_service.create(**self.details())
        self.app.undo()
        second = self.app.orders_service.create(**self.details())
        self.assertNotEqual(first.id, second.id)

    def test_backup_restore_and_preventive_copy(self):
        """Comprueba la restauración y la copia preventiva del estado actual."""
        first_backup = self.app.create_backup()
        self.app.orders_service.create(**self.details())
        preventive = self.app.restore_backup(first_backup)
        self.assertIn(preventive, self.app.storage.list_backups())
        self.assertEqual(len(self.app.orders_service.list_all()), 0)
        self.assertEqual(self.app.inventory.get("R01").stock, 80)

    def test_atomic_save_failure_rolls_back_all_memory(self):
        """Comprueba que un fallo al guardar revierta también la memoria."""
        before = self.app.to_dict()
        original_save = self.app.storage.save

        def fail_save(_data):
            """Simula un error de escritura del almacenamiento."""
            raise StorageError("Fallo de disco simulado")

        self.app.storage.save = fail_save
        with self.assertRaises(StorageError):
            self.app.orders_service.create(**self.details())
        self.app.storage.save = original_save
        self.assertEqual(self.app.to_dict(), before)
        self.assertEqual(Application(self.path).to_dict(), before)

    def test_inventory_protects_catalog_references(self):
        """Impide borrar flores que todavía aparecen en el catálogo."""
        with self.assertRaises(ValueError):
            self.app.inventory.remove("R01")
        self.assertEqual(self.app.inventory.get("R01").stock, 80)

    def test_catalog_crud(self):
        """Verifica alta, edición y eliminación de ramilletes."""
        self.app.catalog.add("C99", "Mini", "pequeno", [("R02", 2)])
        self.assertEqual(self.app.catalog.get("C99").name, "Mini")
        self.app.catalog.edit("C99", "Otro", "pequeno", [("R02", 3)])
        self.assertEqual(self.app.catalog.get("C99").items[0]["quantity"], 3)
        self.app.catalog.remove("C99")
        self.assertIsNone(self.app.catalog.get("C99"))

    def test_money_precision(self):
        """Verifica conversión de precios y redondeo de impuestos."""
        self.assertEqual(parse_price("1,25"), 125)
        self.assertEqual(calculate_tax(101), 15)
        with self.assertRaises(ValueError):
            parse_price("1.234")



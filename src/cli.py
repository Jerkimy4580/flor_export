"""Menús de consola; la lógica de negocio permanece en servicios separados."""

from .models import PRIORITY_LABELS, SIZE_RULES, STATUS_LABELS, money, parse_price
from .storage import StorageError


def title(text):
    """Imprime un encabezado para separar las pantallas del menú."""
    print("\n" + "=" * 58)
    print(text)
    print("=" * 58)


def text_input(message):
    """Lee texto y elimina espacios sobrantes al principio y al final."""
    return input(message).strip()


def number_input(message, minimum=0):
    """Solicita un entero que cumpla el mínimo indicado."""
    while True:
        raw = text_input(message)
        if raw.isdigit() and int(raw) >= minimum:
            return int(raw)
        print(f"Ingrese un entero mayor o igual que {minimum}.")


def price_input(message):
    """Solicita un precio y repite la entrada si no es válido."""
    while True:
        try:
            return parse_price(text_input(message))
        except ValueError as error:
            print("Error:", error)


def size_input():
    """Solicita uno de los tamaños de ramillete disponibles."""
    print("Tamaños: pequeno (1-6), mediano (7-12), grande (13-24) flores")
    while True:
        size = text_input("Tamaño: ").lower()
        if size in SIZE_RULES:
            return size
        print("El tamaño no existe. Escriba pequeno, mediano o grande.")


def print_flowers(app):
    """Muestra el inventario y señala las flores con stock bajo."""
    title("INVENTARIO DE FLORES")
    print(f"{'Código':<9}{'Flor':<17}{'Color':<14}{'Stock':>7}{'Precio':>9}{'Min':>6}")
    for flower in app.inventory.list_all():
        alert = " *BAJO*" if flower.stock <= flower.minimum else ""
        print(f"{flower.id:<9}{flower.name:<17}{flower.color:<14}"
              f"{flower.stock:>7}{money(flower.price_cents):>9}{flower.minimum:>6}{alert}")


def print_bouquets(app):
    """Muestra cada ramillete y las flores que lo componen."""
    title("CATÁLOGO DE RAMILLETES")
    for bouquet in app.catalog.list_all():
        print(f"{bouquet.id}  {bouquet.name} ({bouquet.size})")
        for line in bouquet.items:
            flower = app.inventory.get(line["flower_id"])
            description = f"{flower.name} {flower.color}" if flower else "Flor no disponible"
            print(f"   {line['quantity']} x {description} [{line['flower_id']}]")


def print_order(order):
    """Muestra los datos, artículos, costos y seguimiento de un pedido."""
    title(f"PEDIDO {order.id}")
    print(f"Cliente: {order.customer}  |  Teléfono: {order.phone}")
    print(f"Destino: {order.country}, {order.address}")
    print(f"Ramillete: {order.bouquet_name} ({order.size})")
    print(f"Estado: {STATUS_LABELS[order.status]}  |  Prioridad: {PRIORITY_LABELS[order.priority]}")
    for item in order.items:
        print(f"  {item.quantity} x {item.flower_name} {item.color} "
              f"[{item.flower_id}] a {money(item.price_cents)}")
    print(f"Flores: {money(order.subtotal_cents)}")
    print(f"Empaque: {money(order.packaging_cents)}")
    print(f"IVA 15%: {money(order.tax_cents)}")
    print(f"TOTAL: {money(order.total_cents)}")
    print(f"Guía: {order.tracking_code or 'Aún no asignada'}")
    print(f"Registrado: {order.created_at}")


def print_orders(app):
    """Muestra una fila resumida por cada pedido registrado."""
    title("PEDIDOS REGISTRADOS")
    orders = app.orders_service.list_all()
    if not orders:
        print("Todavía no existen pedidos.")
    for order in orders:
        print(f"{order.id:<9} {order.customer:<20} {STATUS_LABELS[order.status]:<17} "
              f"{order.country:<16} {money(order.total_cents)}")


def input_items():
    """Solicita códigos de flores y cantidades hasta recibir ENTER vacío."""
    print("Agregue códigos de flores. Pulse ENTER en el código para terminar.")
    items = []
    while True:
        flower_id = text_input("Código de flor (ENTER para finalizar): ").upper()
        if not flower_id:
            return items
        quantity = number_input("Cantidad: ", minimum=1)
        items.append((flower_id, quantity))


def bouquet_choice(app):
    """Permite escoger un ramillete del catálogo o crear uno personalizado."""
    print("1. Elegir un ramillete del catálogo")
    print("2. Armar un ramillete personalizado")
    option = text_input("Opción: ")
    if option == "1":
        print_bouquets(app)
        bouquet = app.catalog.get(text_input("Código del ramillete: "))
        if not bouquet:
            raise ValueError("El ramillete indicado no existe.")
        items = [(line["flower_id"], line["quantity"]) for line in bouquet.items]
        return bouquet.name, bouquet.size, items
    if option == "2":
        print_flowers(app)
        name = text_input("Nombre para su ramillete: ") or "Personalizado"
        size = size_input()
        return name, size, input_items()
    raise ValueError("Seleccione 1 o 2.")


def input_order(app):
    """Recopila los datos del cliente y la composición del pedido."""
    name, size, items = bouquet_choice(app)
    return {
        "customer": text_input("Cliente: "),
        "phone": text_input("Teléfono (10 dígitos): "),
        "country": text_input("País de destino: "),
        "address": text_input("Dirección de entrega: "),
        "bouquet_name": name, "size": size, "items": items,
        "priority": number_input("Prioridad 1=urgente, 2=normal, 3=baja: ", minimum=1),
    }


def confirm(message="¿Confirmar? (s/n): "):
    """Devuelve si la respuesta del usuario fue afirmativa."""
    return text_input(message).lower() == "s"


def inventory_menu(app):
    """Gestiona las opciones de consulta y mantenimiento del inventario."""
    while True:
        title("MÓDULO 1  INVENTARIO")
        print("1. Ver inventario     2. Registrar flor")
        print("3. Recibir lote       4. Editar flor")
        print("5. Eliminar flor      6. Alertas de stock")
        print("0. Volver")
        option = text_input("Opción: ")
        if option == "0":
            return
        try:
            if option == "1":
                print_flowers(app)
            elif option == "2":
                flower_id = text_input("Código: ")
                name = text_input("Nombre: ")
                color = text_input("Color: ")
                quantity = number_input("Stock inicial: ")
                price = price_input("Precio por unidad ($): ")
                minimum = number_input("Alerta al llegar a: ")
                app.inventory.add(flower_id, name, color, quantity, price, minimum)
                print("Flor registrada.")
            elif option == "3":
                app.inventory.restock(text_input("Código: "), number_input("Unidades recibidas: ", 1))
                print("Lote recibido, inventario actualizado.")
            elif option == "4":
                code = text_input("Código a editar: ")
                app.inventory.edit(code, text_input("Nuevo nombre: "), text_input("Nuevo color: "),
                                   price_input("Precio ($): "), number_input("Mínimo: "))
                print("Flor actualizada.")
            elif option == "5":
                code = text_input("Código a eliminar: ")
                if confirm("¿Eliminar flor? (s/n): "):
                    app.inventory.remove(code)
                    print("Flor eliminada.")
            elif option == "6":
                alerts = app.inventory.low_stock()
                if not alerts:
                    print("No hay alertas de stock bajo.")
                for flower in alerts:
                    print(f"{flower.id}: {flower.name} {flower.color}, "
                          f"quedan {flower.stock}; mínimo {flower.minimum}")
            else:
                print("Opción desconocida.")
        except (ValueError, StorageError) as error:
            print("Error:", error)


def catalog_menu(app):
    """Gestiona las opciones de consulta y mantenimiento del catálogo."""
    while True:
        title("CATÁLOGO DE RAMILLETES")
        print("1. Ver catálogo   2. Registrar   3. Modificar   4. Eliminar   0. Volver")
        option = text_input("Opción: ")
        if option == "0":
            return
        try:
            if option == "1":
                print_bouquets(app)
            elif option in ("2", "3"):
                code = text_input("Código del ramillete: ")
                name = text_input("Nombre: ")
                size = size_input()
                print_flowers(app)
                items = input_items()
                if option == "2":
                    app.catalog.add(code, name, size, items)
                else:
                    app.catalog.edit(code, name, size, items)
                print("Catálogo actualizado.")
            elif option == "4":
                code = text_input("Código a eliminar: ")
                if confirm():
                    app.catalog.remove(code)
                    print("Ramillete eliminado.")
            else:
                print("Opción desconocida.")
        except (ValueError, StorageError) as error:
            print("Error:", error)


def orders_menu(app):
    """Gestiona la creación, consulta y mantenimiento de pedidos."""
    while True:
        title("MÓDULO 2  GESTIÓN DE PEDIDOS")
        print("1. Crear pedido      2. Ver pedidos      3. Buscar y rastrear")
        print("4. Modificar pedido  5. Cancelar pedido  6. Eliminar pedido")
        print("0. Volver")
        option = text_input("Opción: ")
        if option == "0":
            return
        try:
            if option == "1":
                data = input_order(app)
                print_order(app.orders_service.preview(**data))
                if confirm("¿Confirmar la compra y descontar stock? (s/n): "):
                    created = app.orders_service.create(**data)
                    print("Pedido registrado con ID", created.id)
                else:
                    print("Compra descartada; el inventario no cambió.")
            elif option == "2":
                print_orders(app)
            elif option == "3":
                order = app.orders_service.get(text_input("ID del pedido: "))
                if not order:
                    raise ValueError("No existe ese pedido.")
                print_order(order)
                print("Seguimiento:")
                for event in order.events:
                    print(f"  {event['at']}: {STATUS_LABELS.get(event['status'], event['status'])}")
            elif option == "4":
                order_id = text_input("ID del pedido a modificar: ")
                data = input_order(app)
                print_order(app.orders_service.preview(order_id=order_id, **data))
                if confirm("¿Guardar nueva versión? (s/n): "):
                    app.orders_service.edit(order_id, **data)
                    print("Pedido modificado y stock ajustado.")
            elif option == "5":
                order_id = text_input("ID a cancelar: ")
                if confirm("¿Cancelar y devolver flores? (s/n): "):
                    app.orders_service.cancel(order_id)
                    print("Pedido cancelado.")
            elif option == "6":
                order_id = text_input("ID a eliminar: ")
                if confirm("¿Eliminar definitivamente del registro? (s/n): "):
                    app.orders_service.delete(order_id)
                    print("Pedido eliminado y existencias ajustadas.")
            else:
                print("Opción desconocida.")
        except (ValueError, StorageError) as error:
            print("Error:", error)


def shipping_menu(app):
    """Gestiona la preparación, despacho y entrega de pedidos."""
    while True:
        title("MÓDULO 3  LOGÍSTICA Y ENVÍOS")
        print("1. Cola FIFO pendiente    2. Iniciar próxima preparación")
        print("3. Cola de despacho      4. Enviar siguiente por prioridad")
        print("5. Confirmar entrega     0. Volver")
        option = text_input("Opción: ")
        if option == "0":
            return
        try:
            if option == "1":
                queue = app.shipping.pending_queue()
                for order in queue:
                    print(f"{order.id} - {order.customer} - {order.country}")
                if not len(queue):
                    print("Cola vacía.")
            elif option == "2":
                order = app.shipping.prepare_next()
                print(f"En preparación: {order.id}")
            elif option == "3":
                queue = app.shipping.shipping_queue().ordered()
                for order in queue:
                    print(f"{order.id} - {PRIORITY_LABELS[order.priority]} - {order.country}")
                if not queue:
                    print("Cola vacía.")
            elif option == "4":
                order = app.shipping.ship_next()
                print(f"Despachado {order.id}; guía {order.tracking_code}; destino {order.country}")
            elif option == "5":
                order = app.shipping.mark_delivered(text_input("ID entregado: "))
                print(f"Entrega de {order.id} confirmada.")
            else:
                print("Opción desconocida.")
        except (ValueError, StorageError) as error:
            print("Error:", error)


def tools_menu(app):
    """Muestra historial y permite usar respaldos, deshacer y rehacer."""
    while True:
        title("HISTORIAL Y COPIAS DE SEGURIDAD")
        print("1. Ver historial        2. Deshacer última operación")
        print("3. Rehacer operación    4. Crear respaldo TXT")
        print("5. Ver respaldos        6. Restaurar respaldo")
        print("0. Volver")
        option = text_input("Opción: ")
        if option == "0":
            return
        try:
            if option == "1":
                for entry in app.audit[-20:]:
                    print(f"{entry['at']}  {entry['message']}")
                if not app.audit:
                    print("El historial está vacío.")
            elif option == "2":
                if confirm("¿Deshacer el último cambio? (s/n): "):
                    app.undo()
                    print("Cambio deshecho.")
            elif option == "3":
                if confirm("¿Rehacer el cambio? (s/n): "):
                    app.redo()
                    print("Cambio rehecho.")
            elif option == "4":
                print("Respaldo guardado:", app.create_backup())
            elif option == "5":
                backups = app.storage.list_backups()
                print("\n".join(backups) if backups else "No hay respaldos.")
            elif option == "6":
                print("Respaldos disponibles:")
                for name in app.storage.list_backups():
                    print(" -", name)
                name = text_input("Escriba el nombre EXACTO del respaldo: ")
                if confirm("ATENCIÓN: reemplazará los datos actuales. ¿Continuar? (s/n): "):
                    safe = app.restore_backup(name)
                    print("Restauración completada. Copia previa:", safe)
            else:
                print("Opción desconocida.")
        except (ValueError, StorageError) as error:
            print("Error:", error)


def run(app):
    """Muestra el menú principal y dirige al módulo elegido."""
    while True:
        title("SISTEMA DE EXPORTACIÓN DE RAMILLETES  |  JEREMY ARÉVALO")
        print("1. Inventario de flores     2. Catálogo de ramilletes")
        print("3. Gestión de pedidos      4. Logística y envíos")
        print("5. Historial y respaldos   0. Salir")
        option = text_input("Opción: ")
        if option == "0":
            print("Datos guardados en archivos TXT. ¡Hasta pronto!")
            return
        if option == "1":
            inventory_menu(app)
        elif option == "2":
            catalog_menu(app)
        elif option == "3":
            orders_menu(app)
        elif option == "4":
            shipping_menu(app)
        elif option == "5":
            tools_menu(app)
        else:
            print("Opción desconocida.")

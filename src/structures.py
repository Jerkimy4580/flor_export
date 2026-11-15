"""Estructuras explícitas de la materia: nodos, lista, pila y colas."""

from dataclasses import dataclass


@dataclass
class Node:
    """Almacena un valor y la referencia al siguiente nodo."""

    value: object
    next: object = None


class LinkedList:
    """Lista enlazada simple; insertar al final y buscar recorriendo nodos."""

    def __init__(self, values=()):
        """Crea una lista enlazada con los valores recibidos."""
        self.head = None
        self.tail = None
        self.length = 0
        for value in values:
            self.append(value)

    def append(self, value):
        """Agrega un valor al final de la lista."""
        node = Node(value)
        if self.tail is None:
            self.head = node
        else:
            self.tail.next = node
        self.tail = node
        self.length += 1

    def find(self, predicate):
        """Devuelve el primer valor que cumple la condición."""
        for value in self:
            if predicate(value):
                return value
        return None

    def remove(self, predicate):
        """Elimina y devuelve el primer valor que cumple la condición."""
        previous = None
        node = self.head
        while node:
            if predicate(node.value):
                if previous is None:
                    self.head = node.next
                else:
                    previous.next = node.next
                if node is self.tail:
                    self.tail = previous
                self.length -= 1
                return node.value
            previous, node = node, node.next
        return None

    def __iter__(self):
        """Recorre los valores desde el primer nodo."""
        node = self.head
        while node:
            yield node.value
            node = node.next

    def __len__(self):
        """Devuelve la cantidad de elementos."""
        return self.length


class Stack:
    """Pila LIFO enlazada, usada para deshacer y rehacer operaciones."""

    def __init__(self, values=()):
        """Crea una pila con los valores en orden de entrada."""
        self.top = None
        self.length = 0
        for value in values:
            self.push(value)

    def push(self, value):
        """Agrega un valor en la cima de la pila."""
        self.top = Node(value, self.top)
        self.length += 1

    def pop(self):
        """Retira y devuelve el valor de la cima."""
        if self.top is None:
            raise ValueError("La pila está vacía.")
        value = self.top.value
        self.top = self.top.next
        self.length -= 1
        return value

    def peek(self):
        """Consulta la cima sin retirarla."""
        return self.top.value if self.top else None

    def to_list(self):
        """Orden cronológico para guardar en el archivo TXT."""
        values = []
        node = self.top
        while node:
            values.append(node.value)
            node = node.next
        return list(reversed(values))

    def __len__(self):
        """Devuelve la cantidad de elementos."""
        return self.length


class Queue:
    """Cola FIFO con nodos; añadir y retirar cuesta O(1)."""

    def __init__(self):
        """Crea una cola FIFO vacía."""
        self.head = None
        self.tail = None
        self.length = 0

    def enqueue(self, value):
        """Agrega un valor al final de la cola."""
        node = Node(value)
        if self.tail is None:
            self.head = node
        else:
            self.tail.next = node
        self.tail = node
        self.length += 1

    def dequeue(self):
        """Retira y devuelve el valor más antiguo."""
        if self.head is None:
            raise ValueError("La cola está vacía.")
        value = self.head.value
        self.head = self.head.next
        if self.head is None:
            self.tail = None
        self.length -= 1
        return value

    def __iter__(self):
        """Recorre la cola desde el elemento más antiguo."""
        node = self.head
        while node:
            yield node.value
            node = node.next

    def __len__(self):
        """Devuelve la cantidad de elementos."""
        return self.length


class PriorityShippingQueue:
    """Tres colas FIFO: urgente, normal y baja; prioridad sin perder orden."""

    def __init__(self, orders):
        """Agrupa pedidos listos para envío y conserva su orden de llegada."""
        self.queues = {1: Queue(), 2: Queue(), 3: Queue()}
        for order in sorted(orders, key=lambda item: item.created_seq):
            if order.status == "en_preparacion":
                self.queues[order.priority].enqueue(order)

    def next(self):
        """Retira el siguiente pedido según su prioridad."""
        for priority in (1, 2, 3):
            if len(self.queues[priority]):
                return self.queues[priority].dequeue()
        return None

    def ordered(self):
        """Devuelve los pedidos pendientes agrupados por prioridad."""
        return [order for priority in (1, 2, 3) for order in self.queues[priority]]

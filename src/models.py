"""Modelos de datos y reglas sencillas compartidas por los módulos."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


TAX_PERCENT = 15  # IVA académico configurable.
SIZE_RULES = {
    "pequeno": (1, 6, 200),
    "mediano": (7, 12, 400),
    "grande": (13, 24, 600),
}
STATUS_LABELS = {
    "pendiente": "Pendiente",
    "en_preparacion": "En preparación",
    "enviado": "Enviado",
    "entregado": "Entregado",
    "cancelado": "Cancelado",
}
PRIORITY_LABELS = {1: "Urgente", 2: "Normal", 3: "Baja"}


def now_text():
    """Fecha y hora local del sistema, usadas en el historial."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def money(cents):
    """Presenta un valor entero de centavos sin errores de decimales."""
    return f"${cents / 100:.2f}"


def parse_price(value):
    """Transforma dólares a centavos; rechaza precios negativos o inválidos."""
    try:
        number = Decimal(str(value).strip().replace(",", "."))
        if not number.is_finite() or number < 0:
            raise ValueError
        cents = number * 100
        if cents != cents.quantize(Decimal("1")):
            raise ValueError("El precio debe tener máximo dos decimales.")
        return int(cents)
    except (InvalidOperation, ValueError) as error:
        raise ValueError("Ingrese un precio válido de hasta dos decimales.") from error


def required(text, name):
    """Valida campos de texto obligatorios."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"El campo {name} es obligatorio.")
    return text.strip()


def positive_int(value, name, allow_zero=False):
    """Evita cantidades negativas, flotantes y booleanos."""
    if isinstance(value, bool) or not str(value).isdigit():
        raise ValueError(f"{name} debe ser un número entero válido.")
    number = int(value)
    if number < (0 if allow_zero else 1):
        raise ValueError(f"{name} debe ser {'no negativo' if allow_zero else 'mayor que cero'}.")
    return number


@dataclass
class Flower:
    """Representa una variedad de flor y sus existencias."""

    id: str
    name: str
    color: str
    stock: int
    price_cents: int
    minimum: int = 10

    def to_dict(self):
        """Convierte la flor a un diccionario para guardarla."""
        return asdict(self)


@dataclass
class Bouquet:
    """Define un ramillete del catálogo y las flores que lo componen."""

    id: str
    name: str
    size: str
    items: list  # Ejemplo: [{"flower_id": "R01", "quantity": 4}]

    def to_dict(self):
        """Convierte el ramillete a un diccionario para guardarlo."""
        return asdict(self)


@dataclass
class OrderItem:
    """Guarda una línea de flores incluida en un pedido."""

    flower_id: str
    flower_name: str
    color: str
    quantity: int
    price_cents: int

    def to_dict(self):
        """Convierte la línea del pedido a un diccionario."""
        return asdict(self)


@dataclass
class Order:
    """Representa un pedido y su información de precio y envío."""

    id: str
    customer: str
    phone: str
    country: str
    address: str
    bouquet_name: str
    size: str
    items: list[OrderItem]
    priority: int
    status: str
    created_seq: int
    created_at: str
    updated_at: str
    subtotal_cents: int
    packaging_cents: int
    tax_cents: int
    total_cents: int
    tracking_code: str = ""
    events: list = field(default_factory=list)

    def to_dict(self):
        """Convierte el pedido y sus artículos a un diccionario."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """Reconstruye un pedido y sus artículos desde un diccionario."""
        return cls(**{**data, "items": [OrderItem(**item) for item in data["items"]]})


def calculate_tax(amount_cents):
    """IVA redondeado al centavo con la regla habitual HALF UP."""
    tax = Decimal(amount_cents) * Decimal(TAX_PERCENT) / Decimal(100)
    return int(tax.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

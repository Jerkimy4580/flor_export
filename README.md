# Sistema de Gestión de Pedidos para una Exportadora de Ramilletes de Flores

**Autor:** Jeremy Arévalo  
**Lenguaje:** Python 3.10 o superior  

Sistema académico de consola que permite registrar flores, ofrecer ramilletes de catálogo o personalizados, gestionar pedidos, preparar envíos y conservar datos en archivos de texto. Usa programación orientada a objetos, una lista enlazada simple, pilas LIFO y colas FIFO/priorizadas.

## 1. Cómo ejecutar

1. Abre la terminal en la carpeta `flor_export`.
2. Comprueba que Python está instalado:

   ```bash
   python --version
   ```

3. Inicia el programa:

   ```bash
   python main.py
   ```

En Windows, si el comando `python` no funciona, intenta `py main.py`.

Para usar la aplicación de consola no necesitas `pip install`, configurar una base de datos externa ni disponer de Internet. Los datos iniciales se crean en `data/database.txt` cuando se abre por primera vez.



## 2. Estructura del proyecto

```text
flor_export/
├── main.py                   # Inicio y manejo de salida
├── README.md                 # Uso y explicación técnica
├── requirements-documentacion.txt # Dependencias opcionales del informe Word
├── src/
│   ├── models.py             # Flower, Bouquet, Order, OrderItem, reglas y precios
│   ├── structures.py         # Node, LinkedList, Stack, Queue, PriorityShippingQueue
│   ├── storage.py            # Lectura/escritura TXT, guardado seguro y respaldos
│   ├── application.py        # Transacciones, integridad, deshacer y rehacer
│   ├── cli.py                # Menús y presentación en consola
│   └── services/
│       ├── inventory.py      # Flores, reposición y alertas
│       ├── catalog.py        # Plantillas de ramilletes
│       ├── orders.py         # Pedidos, totales y actualización de existencias
│       └── shipping.py       # Colas, prioridades y seguimiento
├── data/
│   ├── database.txt          # Base de datos principal, formato JSON legible
│   └── backups/             # Copias de seguridad .txt
├── tests/
│   └── test_system.py        # Pruebas automáticas
├── documentacion/
│   ├── build_report.py
│   ├── Informe_Critico_FlorExport.docx
│   └── infografias/         # Diagramas individuales por módulo
```

> Nota: los archivos JSON escritos con extensión `.txt` **son archivos de texto normales**, editables con Bloc de notas o VS Code. Se usa una sola base TXT principal porque un pedido modifica simultáneamente su registro y varias existencias; así se puede guardar todo en una sola operación. Los respaldos son otros archivos `.txt` independientes.

## 3. Funciones de cada módulo

### Inventario

- Mostrar flores disponibles con código, nombre, color, stock, precio y mínimo.
- Agregar variedades; impedir códigos y combinaciones nombre/color duplicados.
- Recibir nuevos lotes y actualizar existencias.
- Modificar nombre, color, precio y umbral mínimo.
- Eliminar flores únicamente cuando no estén referenciadas por ramilletes del catálogo o pedidos no cancelados.
- Avisar cuando `stock <= mínimo`.

### Catálogo

- Consultar ramilletes disponibles y su composición.
- Registrar, editar y eliminar ramilletes prediseñados.
- Elegir un ramillete existente o crear uno personalizado al comprar.

### Gestión de pedidos

- Crear, consultar por ID, modificar, cancelar y eliminar pedidos permitidos.
- Seleccionar flores, colores por código, cantidades y tamaño de ramillete.
- Validar datos del comprador (incluye teléfono de 10 dígitos) y stock suficiente.
- **Mostrar un resumen antes de confirmar**, sin descontar existencias durante la vista previa.
- Calcular subtotal, empaque, IVA académico del 15 % y total en centavos enteros.
- Descontar existencias al confirmar; restaurarlas cuando se modifica, cancela o elimina un pedido que aún no se envía.
- Mantener ID único correlativo `P00001`, `P00002`, etc.

### Logística y envíos

- Preparar por orden de llegada **FIFO** los pedidos pendientes.
- Despachar pedidos preparados por prioridad: urgente (1), normal (2), baja (3).
- Mantener orden FIFO cuando dos pedidos tienen la misma prioridad.
- Registrar destino, dirección, estados y código de seguimiento.
- Recorrer `pendiente → en preparación → enviado → entregado`.
- Cancelar únicamente antes del envío; impedir eliminar pedidos enviados o entregados.

### Historial y seguridad

- Guardar un historial de las últimas 100 operaciones.
- Deshacer y rehacer usando pilas enlazadas, con un límite de 30 estados anteriores.
- Crear y listar respaldos `.txt` en `data/backups/`.
- Restaurar un respaldo elegido; antes se crea automáticamente una copia preventiva del estado actual.
- Guardar cada modificación primero en un archivo temporal y reemplazar de forma atómica `database.txt`.

## 4. Ejemplo completo

1. Entra a **Inventario** y consulta el código `R01`: Rosa roja, 80 unidades, $1.50.
2. Entra a **Gestión de pedidos → Crear pedido → Personalizado**.
3. Escribe `pequeno` y selecciona `R01`, cantidad `4`.
4. Introduce un nombre, teléfono de 10 dígitos, país, dirección y prioridad 2.
5. El sistema muestra un resumen, por ejemplo:

   ```text
   4 rosas rojas         4 × $1.50 = $6.00
   Empaque pequeño                  $2.00
   IVA del 15 %                    $1.20
   TOTAL                            $9.20
   ```

6. Confirma con `s`: el stock de `R01` pasa de **80 a 76** y aparece `P00001`.
7. En **Logística**, usa `Iniciar próxima preparación`, después `Enviar siguiente` y finalmente `Confirmar entrega` para `P00001`.
8. Puedes buscar `P00001` y ver el estado, la guía y las fechas de cada transición.

**Importante:** los valores son datos de demostración y el IVA del 15 % es una constante académica, no una validación tributaria para exportaciones reales.

## 5. Estructuras de datos y complejidad

| Operación | Estructura | Complejidad aproximada |
|---|---|---|
| Agregar al final | `LinkedList` con cola de lista | O(1) |
| Buscar o eliminar por código | Lista enlazada simple | O(n) |
| Apilar/desapilar una acción | `Stack` enlazada | O(1) |
| Encolar/desencolar pedido | `Queue` enlazada | O(1) |
| Siguiente despacho preparado | Tres colas por prioridad | O(1) tras construir las colas |
| Reconstruir colas desde pedidos | Clasificación y recorrido | O(n log n) |
| Guardar un cambio completo | Snapshot en archivo TXT | O(n) en tamaño del estado |

Aunque se usan estructuras dinámicas, la búsqueda por código sigue siendo lineal. No se aplica búsqueda binaria directamente en una lista enlazada simple. Para un volumen mucho mayor, convendría un índice por ID y una base de datos transaccional.

## 6. Buenas prácticas aplicadas

- **Responsabilidad única:** modelos, estructuras, almacenamiento, interfaz y servicios separados.
- **Reutilización:** funciones `required`, `positive_int`, `parse_price`, `money`; las dos rutas de pedidos reutilizan `preview`.
- **Encapsulación:** los módulos modifican el estado usando `Application.change`.
- **Consistencia:** si guardar falla, se restaura el estado anterior en memoria y el TXT existente no se reemplaza parcialmente.
- **Validaciones:** el sistema impide cantidades negativas, teléfonos incompletos, IDs duplicados, sobreventa y transiciones de estado incorrectas.
- **Trazabilidad:** códigos únicos, historial de estados y protección contra borrado de pedidos enviados.
- **Pruebas:** `unittest` sin paquetes de terceros.

## 7. Ejecutar las pruebas

Desde `flor_export`, ejecuta:

```bash
python -m unittest discover -s tests -v
```

El conjunto inicial contiene **20 pruebas** para inventario, pedidos, catálogo, envío, prioridad, respaldos, persistencia, pila, cola, lista enlazada y recuperación tras un fallo de disco simulado.

## 8. Copias de seguridad y archivos de datos

El sistema utiliza `data/database.txt` como fuente principal. Sus secciones son `flowers`, `orders`, `bouquets`, `next_id`, `undo`, `redo` y `audit`. El archivo es texto UTF-8 con datos estructurados en JSON; nunca necesitas instalar un servidor.

Para respaldar: menú **Historial y respaldos → Crear respaldo TXT**. Se genera `data/backups/respaldo_AAAAMMDD_HHMMSS_ffffff.txt`.

Para restaurar: menú **Historial y respaldos → Restaurar respaldo**, escribe el nombre exacto y confirma. El programa crea primero una copia del contenido actual para poder recuperarlo si la elección fue incorrecta.

No edites manualmente `database.txt` mientras el programa está abierto. Los respaldos deben conservarse fuera del equipo para protegerse ante una pérdida física del disco.

## 9. Limitaciones y mejoras futuras

Este sistema está diseñado para **un solo proceso local**. No incorpora inicio de sesión, sincronización entre equipos, cobros reales, transportistas externos ni bloqueo entre varios procesos escribiendo el mismo TXT. La fotografía completa de datos por cambio y el historial de deshacer son prácticos para una tarea académica, pero consumen más memoria y tiempo al crecer el volumen. En una versión empresarial, se introducirían índices, una base de datos SQL con transacciones, autenticación, backups programados y una API, manteniendo los servicios separados.

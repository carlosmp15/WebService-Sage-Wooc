# WooCommerce-Sage Connector
Este proyecto ofrece un servicio web que facilita la integración bidireccional entre WooCommerce y Sage. Utilizando Python y la API de WooCommerce, permite gestionar la importación, actualización y eliminación de metadatos de manera eficiente.

Este conector garantiza una sincronización efectiva de datos entre ambas plataformas, facilitando la gestión de productos, pedidos y clientes. Es ideal para mantener actualizados los registros en tiempo real y optimizar los procesos administrativos de tu tienda online y sistema contable.

## Características
- **Importación de metadatos**: Sincroniza los datos desde Sage a WooCommerce y viceversa.
- **Actualización de metadatos**: Actualiza los metadatos en ambas direcciones.
- **Eliminación de metadatos**: Elimina datos de WooCommerce o Sage según sea necesario.
- **Bidireccional**: Soporte para sincronización en ambos sentidos.

## Requisitos
- Python 3.8 o superior.
- WooCommerce REST API.
- Sage 200.

## API WooCommerce
El servicio web expone una API RESTful. A continuación, algunos endpoints principales:

- GET /api/woocommerce/products: Lista todos los productos de WooCommerce.
- POST /api/sage/orders: Crea un nuevo pedido en WooCommerce.
- PUT /api/woocommerce/customers/{id}: Actualiza un cliente en WooCommerce.
- DELETE /api/sage/products/{id}: Elimina un producto de WooCommerce.

Consulta la [documentación](https://woocommerce.com/document/woocommerce-rest-api/) de la API para más detalles.

<footer>
  <hr>
  <p style="text-align: center;">
    <em>WebService-WooCommerce-Sage</em> | <a href="https://github.com/carlosmp15" target="_blank">@carlosmp15</a>
  </p>
</footer>

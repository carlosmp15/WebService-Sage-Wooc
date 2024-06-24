# -*- coding: utf-8 -*-

import json
import os.path
import pyodbc
from woocommerce import API


def get_wc_api():
    try:
        wc_api = API(
            url="https://www.tutiendaonline.com/",
            consumer_key="ck_xxxxxxxxxxxxxxxxxxxxxxx",
            consumer_secret="cs_xxxxxxxxxxxxxxxxxxxx",
            wp_api=True,
            version="wc/v3"
        )
        return wc_api
    except Exception as e:
        print("Error de conexion:", e)
        return None


def show_orders(wc_api):
    try:
        response = wc_api.get("orders")
        if response.status_code != 200:
            print("Error al obtener los pedidos:", response.json())
            return None
        else:
            orders = response.json()
            print(json.dumps(orders, indent=4))

            return orders
    except Exception as e:
        print("Error al obtener pedidos:", e)
        return None


def add_order(wc_api, orders):
    try:
        # verifica si el json existe
        if not os.path.exists(orders):
            print(f"Error: El archivo JSON '{orders}' especificado no existe.")
            return

        # carga pedidos desde json
        with open(orders, encoding='utf-8') as file:
            orders_data = json.load(file)

        # existe conexion con wordpress
        if wc_api is None:
            print("Error: La conexion a la API de WooCommerce no se ha establecido correctamente.")
            return

        # crea nuevos pedidos desde el json
        for order in orders_data:
            nuevo_pedido_creado = wc_api.post("orders", order)
            if nuevo_pedido_creado.status_code == 201:
                print("Pedido creado con exito.")
            else:
                print("Error al crear el pedido:", nuevo_pedido_creado.json())
    except Exception as e:
        print("Error al agregar pedidos:", e)


def update_orders(wc_api, nuevo_pedido_json):
    # existe el json
    if not os.path.exists(nuevo_pedido_json):
        print("El archivo JSON especificado no existe.")
        return

    try:
        # muestra pedidos disponibles
        pedidos_disponibles = show_orders(wc_api)
        if pedidos_disponibles:
            with open(nuevo_pedido_json, 'r', encoding='utf-8') as file:
                nuevo_pedido = json.load(file)

            # busca el pedido en la lista de pedidos disponibles
            pedido_encontrado = False
            for cliente in pedidos_disponibles:
                id_pedido_modificar = str(cliente['id'])
                if id_pedido_modificar == nuevo_pedido.get('id'):
                    wc_api.put(f"orders/{id_pedido_modificar}", nuevo_pedido)
                    print("Pedido modificado con exito:")
                    pedido_encontrado = True
                    break

            if not pedido_encontrado:
                print("No se encontro ningun pedido para actualizar.")
    except Exception as e:
        print("Error al modificar pedidos:", e)


def remove_orders(wc_api, pedidos_eliminar):
    if not os.path.exists(pedidos_eliminar):
        print("El archivo JSON especificado no existe.")
        return

    try:
        pedidos_disponibles = show_orders(wc_api)
        if pedidos_disponibles:
            with open(pedidos_eliminar, 'r', encoding='utf-8') as file:
                ids_a_eliminar = json.load(file)

            # verifica si se proporcionaron IDs en el JSON
            if not ids_a_eliminar:
                print("No se proporcionaron IDs de pedidos en el archivo JSON.")
                return

            for id_pedido_eliminar in ids_a_eliminar:
                for pedido in pedidos_disponibles:
                    if str(pedido['id']) == id_pedido_eliminar:
                        response = wc_api.delete(f"orders/{id_pedido_eliminar}?force=true")
                        if response.status_code == 200:
                            print(f"Pedido con ID {id_pedido_eliminar} eliminado con exito.")
                        else:
                            print(f"Error al eliminar el pedido con ID {id_pedido_eliminar}: {response.json()}")
                        break
                else:
                    print(f"No se encontro ningun pedido con el ID {id_pedido_eliminar}.")
    except Exception as e:
        print("Error al eliminar pedidos:", e)


def check_exist_order(cursor, codigo_pedido, tabla, campo):
    cursor.execute("SELECT COUNT(*) FROM " + tabla + " WHERE CodigoEmpresa = 3 AND " + campo + " = ?", (codigo_pedido,))
    row = cursor.fetchone()

    # Si existe el codigo_pedido en bd devuelve true / false
    return row[0] > 0


def insert_document_header(pedidos):
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        # cadena de conexion
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()
        if conn:
            print("Se ha establecido conexión con la BD!\n")

            for pedido in pedidos:
                id_pedido = int(pedido.get('id'))
                id_cliente = int(pedido.get('customer_id'))
                nombre = pedido.get('billing', {}).get('first_name')
                nombre_envio = pedido.get('shipping', {}).get('first_name')
                telefono_envio = pedido.get('shipping', {}).get('phone')
                importe = pedido.get('total')
                fecha_documento = pedido.get('date_created')
                fecha_creacion = pedido.get('date_created')
                ej_doc = fecha_creacion[2:4]
                num_doc = id_pedido
                fecha_pago = pedido.get('date_paid')
                fecha_completado = pedido.get('date_completed')
                domicilio = pedido.get('billing', {}).get('address_1')
                domicilio_envio = pedido.get('shipping', {}).get('address_1')
                municipio = pedido.get('billing', {}).get('city')
                municipio_envio = pedido.get('shipping', {}).get('city')
                cp = pedido.get('billing', {}).get('postcode')
                cp_envio = pedido.get('shipping', {}).get('postcode')
                pais_envio = pedido.get('shipping', {}).get('country')
                codigo_divisa = pedido.get('currency')
                observaciones = pedido.get('customer_note')

                if not check_exist_order(cursor, id_pedido, "CabeceraAlbaranCliente", "NumeroAlbaran"):
                    cursor.execute(
                        "INSERT INTO TmpIME_CabeceraDocumento (CodigoEmpresa, "
                        "EjercicioDocumento, SerieDocumento, NumeroDocumento, CodigoCliente, Nombre, NombreEnvios,"
                        " TelefonoEnvios, ImporteCobroPago, FechaDocumento, FechaCreacion, FechaCobroPago, FechaFin,"
                        " Domicilio, DomicilioEnvios, Municipio, MunicipioEnvios, CodigoPostal, CodigoPostalEnvios, "
                        "NacionEnvios, CodigoDivisa, ObservacionesCliente, IdProcesoIME, CodigoDocumentoLc) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (3, ej_doc, 'WP', num_doc, id_cliente, nombre, nombre_envio,
                         telefono_envio, importe, fecha_documento, fecha_creacion, fecha_pago,
                         fecha_completado, domicilio, domicilio_envio, municipio,
                         municipio_envio, cp, cp_envio, pais_envio,
                         codigo_divisa, observaciones,
                         "00000000-0000-0000-0000-000000000001", 'ALC'))

                    conn.commit()
                    print(f"Cabecera de documento con ID {id_pedido} insertado correctamente.")
                else:
                    print(f"La cabecera de documento {id_pedido} ya existe en la base de datos.")

        else:
            print("No se ha establecido conexión con la BD...")

        conn.close()
    except Exception as e:
        print(e)


def insert_document_lines(pedidos):
    server = '192.168.200.35'
    database = 'SILVER'
    username = 'logic'
    password = 'Sage2009+'

    try:
        # cadena de conexión
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        if conn:
            print("Conexión establecida con la base de datos!\n")

            for pedido in pedidos:
                id_pedido = int(pedido.get('id'))
                id_cliente = int(pedido.get('customer_id'))
                fecha_creacion = pedido.get('date_created')
                ej_doc = fecha_creacion[2:4]

                if not check_exist_order(cursor, id_pedido, "LineasAlbaranCliente", "NumeroAlbaran"):
                    # iterar sobre los productos en la línea de items
                    for item in pedido.get('line_items', []):
                        id_producto = int(item.get('product_id'))
                        precio = float(item.get('price'))
                        unidades = item.get('quantity')

                        # insertar cada producto como una línea de documento
                        cursor.execute(
                            "INSERT INTO TmpIME_LineasDocumento (CodigoEmpresa,"
                            " NumeroDocumento, FechaDocumento, EjercicioDocumento, SerieDocumento, "
                            "CodigodelCliente, CodigoArticulo, Precio, Unidades, IdProcesoIME, "
                            "CodigoDocumentoLc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (3, id_pedido, fecha_creacion, ej_doc, 'WP', id_cliente,
                             id_producto, precio, unidades, "00000000-0000-0000-0000-000000000001", "ALC"))

                    print(f"Linea de documento con ID {id_pedido} insertado correctamente.")
                    conn.commit()
                else:
                    print(f"La linea de documento con ID {id_pedido} ya existe en la base de datos.")

        else:
            print("No se pudo establecer conexión con la base de datos...")

        conn.close()
    except Exception as e:
        print(e)


# add_order(get_wc_api(), "json/nuevo_pedido.json")
# show_orders(get_wc_api())
# update_orders(get_wc_api(), "json/mod_pedido.json")
remove_orders(get_wc_api(), "json/pedidos_elim.json")
# insert_document_header(show_orders(get_wc_api()))
# insert_document_lines(show_orders(get_wc_api()))

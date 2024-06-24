#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyodbc
from woocommerce import API


# Obtiene un objeto API Woocommerce para conectar con la API
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


# Obtiene un json con todas los clientes de Woocommerce
def obtener_clientes_woocommerce(wc_api):
    try:
        page = 1
        all_products = []

        while True:
            response = wc_api.get("customers", params={"page": page})
            if response.status_code != 200:
                print("Error al obtener los clientes:", response.json())
                return None

            categories = response.json()
            all_products.extend(categories)

            # Verificar si hay más páginas
            headers = response.headers
            if "Link" not in headers or "rel=\"next\"" not in headers["Link"]:
                break  # No hay más páginas, salir del bucle

            page += 1

        return all_products
    except Exception as e:
        print("Error al obtener clientes:", e)
        return None


def obt_nombre(nombre_completo):
    # Dividir el nombre completo en palabras
    palabras = nombre_completo.split()

    # El primer elemento es el nombre
    nombre = palabras[0]

    return nombre


def obt_apellidos(nombre_completo):
    # Dividir el nombre completo en palabras
    palabras = nombre_completo.split()

    # Los apellidos son todas las palabras excepto el primer nombre
    apellidos = " ".join(palabras[1:])

    return apellidos


# Obtiene un json con unos campos especificos de la bd de Sage
def obtener_clientes_bd():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta = ("SELECT FechaAlta, Nombre, Email1, CodigoCliente, CodigoCadena_, Domicilio, CodigoPostal, "
                    "Municipio, Provincia, Nacion, Telefono "
                    "FROM Clientes WHERE CodigoEmpresa = 101")

        # Ejecutar la consulta SQL
        cursor.execute(consulta)

        # Obtener los datos seleccionados
        datos_desde_bd = cursor.fetchall()

        conn.close()

        # Convertir los datos a una lista de diccionarios
        datos_json = []
        for fila in datos_desde_bd:
            fila_json = {
                'cod_cliente': fila[3],
                'id_wooc': fila[4],
                'date_created': str(fila[0]),
                'first_name': obt_nombre(fila[1]),
                'last_name': obt_apellidos(fila[1]),
                'email': fila[2],
                "billing": {
                    "first_name": obt_nombre(fila[1]),
                    "last_name": obt_apellidos(fila[1]),
                    "address_1": fila[5],
                    "city": fila[7],
                    "postcode": fila[6],
                    "country": fila[9].capitalize(),
                    "state": fila[8],
                    "email": fila[2],
                    "phone": fila[10]
                },
                "shipping": {
                    "first_name": obt_nombre(fila[1]),
                    "last_name": obt_apellidos(fila[1]),
                    "address_1": fila[5],
                    "city": fila[7],
                    "postcode": fila[6],
                    "country": fila[9].capitalize(),
                    "state": fila[8],
                    "phone": fila[10]
                }
            }
            datos_json.append(fila_json)
        return datos_json

    except pyodbc.Error as e:
        print(e)
        return None


# Importa los clientes desde bd Sage a Woocommerce
def importar_clientes(wc_api):
    clientes_bd = obtener_clientes_bd()
    if wc_api is None:
        print("No se pudo obtener la API de WooCommerce. Verifica la conexión.")
        return

    if not clientes_bd:
        print("No se pudieron obtener los clientes de la base de datos.")
        return

    try:
        server = '127.0.0.1'
        database = 'DB'
        username = 'user'
        password = 'password'

        conn_sage = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)

        cursor_sage = conn_sage.cursor()

        for cliente in clientes_bd:
            # Eliminar la clave "id_wooc" del cliente
            id_cliente_wooc = cliente.pop('id_wooc', None)

            # Guardar el cod_cliente para usarlo en la actualización de Sage
            cod_cliente = cliente.pop('cod_cliente', None)

            if id_cliente_wooc:
                # Verificar si el cliente ya existe en WooCommerce por su id
                existing_customer = wc_api.get(f"customers/{id_cliente_wooc}")

                if existing_customer.status_code == 200 and existing_customer.json():
                    print(f"El cliente '{cliente['first_name']} {cliente['last_name']}' ya existe en WooCommerce.")
                    continue  # Pasar al siguiente cliente

            # Insertar el cliente en WooCommerce
            response = wc_api.post("customers", cliente)

            if response.status_code == 201:
                print(f"Cliente '{cliente['first_name']} {cliente['last_name']}' insertado con éxito.")

                # Obtener el ID del cliente insertado en WooCommerce
                datos_cliente = response.json()
                id_cliente_wooc = datos_cliente.get("id")

                # Actualizar bd de Sage con el id cliente de WooCommerce usando el campo CodigoCadena_
                if cod_cliente:
                    update_query = (f"UPDATE Clientes SET CodigoCadena_ = '{id_cliente_wooc}'"
                                    f" WHERE CodigoCliente = '{cod_cliente}' AND CodigoEmpresa = 101")
                    cursor_sage.execute(update_query)
                    conn_sage.commit()
            else:
                print(
                    f"Error al insertar el cliente '{cliente['first_name']} {cliente['last_name']}'. "
                    f"Código de estado: {response.status_code}")

    except Exception as e:
        print("Error al insertar los clientes:", e)


# Actualiza los clientes modificados de Sage a Woocommerce (nombre, apellidos, email)
def actualizar_clientes(wc_api):
    # Obtener artículos de la base de datos de Sage
    clientes_sage = obtener_clientes_bd()

    if not clientes_sage:
        print("No se pudieron obtener los artículos de Sage.")
        return

    for cliente_sage in clientes_sage:
        # Codigo alternativo en Sage = id articulo Woocommerce
        id_bd_wooc = cliente_sage["id_wooc"]
        nombre_sage = cliente_sage["first_name"]
        apellidos_sage = cliente_sage["last_name"]
        email_sage = cliente_sage["email"]
        tlf_sage = cliente_sage["billing"]["phone"]
        domicilio_sage = cliente_sage["billing"]["address_1"]
        provincia_sage = cliente_sage["billing"]["state"]
        municipio_sage = cliente_sage["billing"]["city"]
        cp_sage = cliente_sage["billing"]["postcode"]

        # Si el id Woocommerce en Sage está vacío no esta importado ese cliente en WooCommerce
        try:
            # Obtener el artículo específico de WooCommerce
            response = wc_api.get(f"customers/{id_bd_wooc}")

            if response.status_code == 200:
                cliente_wooc = response.json()
            else:
                print(f"El cliente con id {id_bd_wooc} no existe en WooCommerce.")
                continue  # Pasar al siguiente cliente

            id_wooc = cliente_wooc["id"]
            nombre_wooc = cliente_wooc["first_name"]
            apellidos_wooc = cliente_wooc["last_name"]
            email_wooc = cliente_wooc["email"]
            tlf_wooc = cliente_wooc["billing"]["phone"]
            domicilio_wooc = cliente_wooc["billing"]["address_1"]
            provincia_wooc = cliente_wooc["billing"]["state"]
            municipio_wooc = cliente_wooc["billing"]["city"]
            cp_wooc = cliente_wooc["billing"]["postcode"]

            # Si el nombre, apellidos, email, tlf, domicilio, provincia, municipio o cp
            # son diferentes, actualizarlos
            if (int(id_wooc) == int(id_bd_wooc) and nombre_wooc != nombre_sage or apellidos_wooc != apellidos_sage
                    or email_wooc != email_sage or tlf_wooc != tlf_sage or domicilio_wooc != domicilio_sage or
                    provincia_wooc != provincia_sage or municipio_wooc != municipio_sage or cp_wooc != cp_sage):
                try:
                    cliente_data = {
                        'first_name': nombre_sage,
                        'last_name': apellidos_sage,
                        'email': email_sage,
                        "billing": {
                            "first_name": nombre_sage,
                            "last_name": apellidos_sage,
                            "address_1": domicilio_sage,
                            "city": municipio_sage,
                            "postcode": cp_sage,
                            "state": provincia_sage,
                            "email": email_sage,
                            "phone": tlf_sage
                        },
                        "shipping": {
                            "first_name": nombre_sage,
                            "last_name": apellidos_sage,
                            "address_1": domicilio_sage,
                            "city": municipio_sage,
                            "postcode": cp_sage,
                            "state": provincia_sage,
                            "phone": tlf_sage
                        }
                    }

                    # Actualizar nombre, apellidos y email del cliente con el método put de la API
                    response_put = wc_api.put(f"customers/{id_wooc}", cliente_data)
                    if response_put.status_code == 200:
                        print(f"Cliente actualizado en WooCommerce: {nombre_sage} {apellidos_sage}")
                    else:
                        print(
                            f"Error al actualizar el cliente en WooCommerce. Código de estado: {response_put.status_code}")
                except Exception as e:
                    print(f"Error al actualizar el cliente en WooCommerce: {e}")
        except Exception as e:
            print(f"Error al obtener el cliente de WooCommerce con ID {id_wooc}: {e}")


# print(obtener_clientes_woocommerce(get_wc_api()))
# print(obtener_clientes_bd())
importar_clientes(get_wc_api())
actualizar_clientes(get_wc_api())

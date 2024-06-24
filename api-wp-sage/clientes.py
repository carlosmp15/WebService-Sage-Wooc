#!/usr/bin/env python
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


def show_customers(wc_api):
    try:
        response = wc_api.get("customers")
        if response.status_code != 200:
            print("Error al obtener los clientes:", response.json())
            return None
        else:
            customers = response.json()
            print(json.dumps(customers, indent=4, ensure_ascii=False).encode('utf-8').decode())

            return customers
    except Exception as e:
        print("Error al obtener clientes:", e)
        return None


def add_customer(wc_api, clientes):
    try:
        # existe el json
        if not os.path.exists(clientes):
            print(f"Error: El archivo JSON '{clientes}' especificado no existe.")
            return

        # carga clientes desde json
        with open(clientes, encoding='utf-8') as file:
            clientes_data = json.load(file)

        # existe conexion con wordpress
        if wc_api is None:
            print("Error: La conexion a la API de WooCommerce no se ha establecido correctamente.")
            return

        # crea nuevos clientes desde json
        for cliente in clientes_data:
            nuevo_cliente_creado = wc_api.post("customers", cliente)
            if nuevo_cliente_creado.status_code == 201:
                print("Cliente creado con exito: Nombre:", cliente['first_name'], " ", cliente['last_name'])
            else:
                print("Error al crear el cliente:", nuevo_cliente_creado.json())
    except Exception as e:
        print("Error al agregar clientes:", e)


def update_customers(wc_api, nuevo_cliente_json):
    # existe el json
    if not os.path.exists(nuevo_cliente_json):
        print("El archivo JSON especificado no existe.")
        return

    try:
        # muestra clientes disponibles
        clientes_disponibles = show_customers(wc_api)
        if clientes_disponibles:
            with open(nuevo_cliente_json, 'r', encoding='utf-8') as file:
                nuevo_cliente = json.load(file)

            # busca el cliente en la lista de clientes disponibles
            cliente_encontrado = False
            for cliente in clientes_disponibles:
                id_cliente_modificar = str(cliente['id'])
                if id_cliente_modificar == nuevo_cliente.get('id'):
                    wc_api.put(f"customers/{id_cliente_modificar}", nuevo_cliente)
                    print("Cliente modificado con exito:")
                    cliente_encontrado = True
                    break

            if not cliente_encontrado:
                print("No se encontro ningún cliente para actualizar.")
    except Exception as e:
        print("Error al modificar clientes:", e)


def remove_customers(wc_api, clientes_eliminar):
    if not os.path.exists(clientes_eliminar):
        print("El archivo JSON especificado no existe.")
        return

    try:
        clientes_disponibles = show_customers(wc_api)
        if clientes_disponibles:
            with open(clientes_eliminar, 'r', encoding='utf-8') as file:
                ids_a_eliminar = json.load(file)

            # verifica si se proporcionaron IDs en el JSON
            if not ids_a_eliminar:
                print("No se proporcionaron IDs de clientes en el archivo JSON.")
                return

            for id_cliente_eliminar in ids_a_eliminar:
                for cliente in clientes_disponibles:
                    if str(cliente['id']) == id_cliente_eliminar:
                        response = wc_api.delete(f"customers/{id_cliente_eliminar}?force=true")
                        if response.status_code == 200:
                            print(f"Cliente con ID {id_cliente_eliminar} eliminado con exito.")
                        else:
                            print(f"Error al eliminar el cliente con ID {id_cliente_eliminar}: {response.json()}")
                        break
                else:
                    print(f"No se encontro ningun cliente con el ID {id_cliente_eliminar}.")
    except Exception as e:
        print("Error al eliminar clientes:", e)


def obtener_primer_apellido(apellidos):
    # divide el nombre completo en palabras
    palabras = apellidos.split()
    # el primer apellido es la primera palabra si hay al menos una palabra
    if len(palabras) >= 1:
        return palabras[0]
    else:
        return ""


def obtener_segundo_apellido(apellidos):
    palabras = apellidos.split()
    if len(palabras) >= 2:
        return palabras[-1]  # Devuelve la última palabra, que es el segundo apellido
    else:
        return ""


def check_exist_customer(cursor, codigo_cliente):
    cursor.execute("SELECT COUNT(*) FROM Clientes WHERE CodigoEmpresa = 3 AND CodigoCliente = ?", (codigo_cliente,))
    row = cursor.fetchone()

    # Si existe el codigo_cliente en bd devuelve true / false
    return row[0] > 0


def insert_customers(clientes):
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

            for cliente in clientes:
                id_cliente = int(cliente.get('id'))
                nombre = cliente.get('first_name')
                apellidos = cliente.get('last_name')
                apellido1 = obtener_primer_apellido(apellidos)
                apellido2 = obtener_segundo_apellido(apellidos)
                email = cliente.get('email')

                if not check_exist_customer(cursor, id_cliente):
                    cursor.execute(
                        "INSERT INTO TmpIME_ClientesProveedores (CodigoEmpresa, CodigoClienteProveedor, "
                        "Nombre, Nombre1, Nombre2, Email1, IdProcesoIME, ClienteOProveedor) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (3, id_cliente, nombre, apellido1, apellido2,
                                                            email, "00000000-0000-0000-0000-000000000001", 'C'))

                    conn.commit()
                    print(f"Cliente con ID {id_cliente} insertado correctamente.")
                else:
                    print(f"El cliente con ID {id_cliente} ya existe en la base de datos.")

        else:
            print("No se ha establecido conexión con la BD...")

        conn.close()
    except Exception as e:
        print(e)


# show_customers(get_wc_api())
# add_customer(get_wc_api(), "json/nuevo_cliente.json")
# update_customers(get_wc_api(), "json/mod_cliente.json")
# remove_customers(get_wc_api(), "json/clientes_elim.json")
insert_customers(show_customers(get_wc_api()))

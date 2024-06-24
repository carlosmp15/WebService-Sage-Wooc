#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import pyodbc
import re
import os
import json
from woocommerce import API


def get_wc_api_v3():
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
        print("Error de conexión:", e)
        return None


def show_products(wc_api):
    try:
        page = 1
        all_products = []

        while True:
            response = wc_api.get("products", params={"page": page})
            if response.status_code != 200:
                print("Error al obtener los productos:", response.json())
                return None

            categories = response.json()
            all_products.extend(categories)

            # Verificar si hay más páginas
            headers = response.headers
            if "Link" not in headers or "rel=\"next\"" not in headers["Link"]:
                break  # No hay más páginas, salir del bucle

            page += 1

        # Imprimir la salida con codificación UTF-8
        print(json.dumps(all_products, indent=4, ensure_ascii=False).encode('utf-8').decode())
        return all_products
    except Exception as e:
        print("Error al obtener productos:", e)
        return None


def add_product(wc_api, productos):
    try:
        # existe el json
        if not os.path.exists(productos):
            print(f"Error: El archivo JSON '{productos}' especificado no existe.")
            return

        # carga productos desde json
        with open(productos, encoding='utf-8') as file:
            productos_data = json.load(file)

        if wc_api is None:
            print("Error: La conexión a la API de WooCommerce no se ha establecido correctamente.")
            return

        # crea nuevos productos desde json
        for producto in productos_data:
            nuevo_producto_creado = wc_api.post("products", producto)
            if nuevo_producto_creado.status_code == 201:
                print("Producto creado con exito: Nombre:", producto['name'], "| Descripción:", producto['description'])
            else:
                print("Error al crear el producto:", nuevo_producto_creado.json())
    except Exception as e:
        print("Error al agregar productos:", e)


def update_products(wc_api, nuevo_producto_json):
    # existe el json
    if not os.path.exists(nuevo_producto_json):
        print("El archivo JSON especificado no existe.")
        return

    try:
        # muestra productos disponibles
        productos_disponibles = show_products(wc_api)
        if productos_disponibles:
            with open(nuevo_producto_json, 'r', encoding='utf-8') as file:
                nuevo_producto = json.load(file)

            # busca el producto en la lista de productos disponibles
            producto_encontrado = False
            for producto in productos_disponibles:
                id_producto_modificar = str(producto['id'])
                if id_producto_modificar == nuevo_producto.get('id'):
                    wc_api.put(f"products/{id_producto_modificar}", nuevo_producto)
                    print("Producto modificado con exito:")
                    producto_encontrado = True
                    break

            if not producto_encontrado:
                print("No se encontro ningun producto para actualizar.")
    except Exception as e:
        print("Error al modificar productos:", e)


def remove_products(wc_api, productos_eliminar):
    if not os.path.exists(productos_eliminar):
        print("El archivo JSON especificado no existe.")
        return

    try:
        productos_disponibles = show_products(wc_api)
        if productos_disponibles:
            with open(productos_eliminar, 'r', encoding='utf-8') as file:
                ids_a_eliminar = json.load(file)

            # verifica si se proporcionaron IDs en el JSON
            if not ids_a_eliminar:
                print("No se proporcionaron IDs de productos en el archivo JSON.")
                return

            for id_producto_eliminar in ids_a_eliminar:
                for producto in productos_disponibles:
                    if str(producto['id']) == id_producto_eliminar:
                        response = wc_api.delete(f"products/{id_producto_eliminar}?force=true")
                        if response.status_code == 200:
                            print(f"Producto con ID {id_producto_eliminar} eliminado con exito.")
                        else:
                            print(f"Error al eliminar el producto con ID {id_producto_eliminar}: {response.json()}")
                        break
                else:
                    print(f"No se encontro ningun producto con el ID {id_producto_eliminar}.")
    except Exception as e:
        print("Error al eliminar productos:", e)


def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def check_exist_product(cursor, codigo_articulo):
    cursor.execute("SELECT COUNT(*) FROM Articulos WHERE CodigoArticulo = ?", (codigo_articulo,))
    row = cursor.fetchone()

    # Si existe el codigo_articulo en bd devuelve true / false
    return row[0] > 0


"""
Función que hace un check para ver donde está la familia o la subfamilia

nomb_columna -> campo de la bd que tendrá la clausula where
tabla -> tabla que vamos a realizar la consulta
n_count -> campo de la bd que se va a contar
valor_where -> valor que tendrá la clausula where

# SELECT COUNT(CodigoFamilia) FROM familias WHERE CodigoEmpresa = 3 AND CodigoFamilia = '1O';
"""


def check_where_family(cursor, nomb_columna, tabla, n_count, valor_where):
    cursor.execute(
        "SELECT COUNT(" + n_count + ") FROM " + tabla + " WHERE CodigoEmpresa = 3 AND " + nomb_columna + "  = ?",
        (valor_where,))
    row = cursor.fetchone()

    # Si existe la familia / subfamilia en bd devuelve true / false
    return row[0] > 0


def eliminar_etiquetas_html(descripcion_html):
    # Expresion regular
    etiqueta_html = re.compile(r'<.*?>')

    # Reemplazar todas las etiquetas HTML por una cadena vacía
    texto_limpio = re.sub(etiqueta_html, '', descripcion_html)

    return texto_limpio


def insert_products(productos):
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        if conn:
            print("Se ha establecido conexión con la BD!\n")
            for product in productos:
                id_producto = int(product.get('id'))
                nombre = product.get('name')
                descripcion = eliminar_etiquetas_html(product.get('description'))
                descripcion_corta = eliminar_etiquetas_html(product.get('short_description'))
                precio_normal = product.get('regular_price')

                familia = ""
                subfamilia = ""

                for categorias in product.get('categories', []):

                    # Se ha encontrado familia
                    if check_where_family(cursor, "CodigoFamilia", "Familias",
                                          "CodigoFamilia", str(categorias.get('id'))):
                        familia = categorias.get('id')

                    # Se ha encontrado la subfamilia
                    elif check_where_family(cursor, "CodigoSubfamilia", "Familias",
                                            "CodigoSubfamilia", str(categorias.get('id'))):
                        subfamilia = categorias.get('id')

                    # Si no tiene subfamilia
                    if subfamilia == "":
                        subfamilia = "**********"

                if not check_exist_product(cursor, str(id_producto)):
                    cursor.execute(
                        "INSERT INTO TmpIME_Articulos (CodigoEmpresa, CodigoArticulo, "
                        "PrecioVenta, DescripcionArticulo, DescripcionLinea, "
                        "ComentarioArticulo, CodigoFamilia, CodigoSubfamilia, IdProcesoIME)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (3, id_producto, precio_normal, nombre,
                         descripcion, descripcion_corta, familia, subfamilia, "00000000-0000-0000-0000-000000000001"))
                    conn.commit()
                    print(f"Producto con ID {id_producto} insertado correctamente.")
                else:
                    print(f"El producto con ID {id_producto} ya existe en la base de datos.")

        else:
            print("No se ha establecido conexión con la BD...")

        conn.close()
    except Exception as e:
        print(e)


# show_products(get_wc_api_v3())
# add_product(get_wc_api_v3(), "json/nuevo_producto_variable.json")
# upload_image("C:\\Users\\Usuario\\Desktop\\info\\img\\img4.jpg")
# update_products(get_wc_api_v3(), "json/mod_producto.json")
# remove_products(get_wc_api_v3(), "json/productos_elim.json")
# insert_products(show_products(get_wc_api_v3()))


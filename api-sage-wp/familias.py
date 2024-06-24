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


# Obtiene un json con unos campos especificos de la bd de Sage para importar a posteriori los datos
def obtener_familias_bd_importar():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta = ("SELECT CodigoFamilia, CodigoSubfamilia, Descripcion, CodigoArancelario"
                    " FROM Familias WHERE CodigoEmpresa = 101 AND CodigoArancelario =''")

        # Ejecutar la consulta SQL
        cursor.execute(consulta)

        # Obtener los datos seleccionados
        datos_desde_bd = cursor.fetchall()

        conn.close()

        # Convertir los datos a una lista de diccionarios
        datos_json = []
        for fila in datos_desde_bd:
            if fila[1] == '**********':
                fila_json = {
                    'codFamilia': fila[0],
                    'codArancelario': fila[3],
                    'name': fila[2],
                    'slug': fila[2].lower(),
                    'parent': 0,
                }
            else:
                fila_json = {
                    'codFamilia': fila[1],
                    'codArancelario': fila[3],
                    'name': fila[2],
                    'slug': fila[2].lower(),
                    'parent': fila[0]
                }
            datos_json.append(fila_json)
        return datos_json

    except pyodbc.Error as e:
        print(e)
        return None


# Comprueba que las subfamilias si tienen el mismo codArancelario que la
# familia padre actualize el codArancelario a vacío
def update_cod_arancelario_mismo_padre():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta = ("SELECT CodigoFamilia, CodigoSubfamilia, Descripcion, CodigoArancelario"
                    " FROM Familias WHERE CodigoEmpresa = 101")

        # Ejecutar la consulta SQL
        cursor.execute(consulta)

        # Obtener los datos seleccionados
        datos_desde_bd = cursor.fetchall()

        # Crear un diccionario para almacenar el código arancelario de cada categoría padre
        codigos_padre = {}

        # Convertir los datos a una lista de diccionarios
        datos_json = []
        for fila in datos_desde_bd:
            if fila[1] == '**********':
                # Guardar el código arancelario de la categoría padre en el diccionario
                codigos_padre[fila[0]] = fila[3]
            else:
                # Si la subcategoría tiene el mismo código arancelario que su categoría padre
                if fila[0] in codigos_padre and fila[3] == codigos_padre[fila[0]]:
                    cursor.execute(f"UPDATE Familias SET CodigoArancelario = '' WHERE CodigoEmpresa = 101 AND "
                                   f"CodigoSubfamilia = '{fila[1]}' AND CodigoArancelario != ''")
                    conn.commit()

        conn.close()

    except pyodbc.Error as e:
        print(e)


def obtener_familias_bd_actualizar():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta = ("SELECT CodigoFamilia, CodigoSubfamilia, Descripcion, CodigoArancelario"
                    " FROM Familias WHERE CodigoEmpresa = 101")

        # Ejecutar la consulta SQL
        cursor.execute(consulta)

        # Obtener los datos seleccionados
        datos_desde_bd = cursor.fetchall()

        conn.close()

        # Convertir los datos a una lista de diccionarios
        datos_json = []
        for fila in datos_desde_bd:
            if fila[1] == '**********':
                fila_json = {
                    'codFamilia': fila[0],
                    'codArancelario': fila[3],
                    'name': fila[2],
                    'slug': fila[2].lower(),
                    'parent': 0,
                }
            else:
                fila_json = {
                    'codFamilia': fila[1],
                    'codArancelario': fila[3],
                    'name': fila[2],
                    'slug': fila[2].lower(),
                    'parent': fila[0]
                }
            datos_json.append(fila_json)
        return datos_json

    except pyodbc.Error as e:
        print(e)
        return None


# Obtiene un json con todas las familias de Woocommerce
def obtener_familias_woocommerce(wc_api):
    try:
        page = 1
        all_categories = []

        while True:
            response = wc_api.get("products/categories", params={"page": page})
            if response.status_code != 200:
                print("Error al obtener las categorías:", response.json())
                return None

            categories = response.json()
            all_categories.extend(categories)

            # Verificar si hay más páginas
            headers = response.headers
            if "Link" not in headers or "rel=\"next\"" not in headers["Link"]:
                break  # No hay más páginas, salir del bucle

            page += 1

        # Imprimir la salida con codificación UTF-8
        return all_categories
    except Exception as e:
        print("Error al obtener categorías:", e)
        return None


# Importar las nuevas familias de bd Sage a Woocommerce
def importar_familias(wc_api):
    if wc_api is None:
        print("No se pudo obtener la API de WooCommerce. Verifica la conexión.")
        return

    try:
        server = '127.0.0.1'
        database = 'DB'
        username = 'user'
        password = 'password'

        conn_sage = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)

        cursor_sage = conn_sage.cursor()
        update_cod_arancelario_mismo_padre()
        familias_bd = obtener_familias_bd_importar()

        if not familias_bd:
            print("No hay nuevas familias para importar en Woocommerce...")
            return

        else:
            for familia in familias_bd:
                parent_id = None  # ID de la familia padre
                print(familia)
                # Si la familia es una subfamilia, buscar la familia padre en Sage y obtener su CodigoArancelario
                if familia['parent'] != 0:
                    cod_arancelario_padre = obtener_codigo_arancelario(cursor_sage, familia['parent'])
                    if cod_arancelario_padre:
                        familias_wooc = obtener_familias_woocommerce(wc_api)
                        for familia_wooc in familias_wooc:
                            if str(familia_wooc['id']) == cod_arancelario_padre:
                                parent_id = familia_wooc['id']
                                break
                        else:
                            print(f"No se pudo encontrar la familia padre para la subfamilia {familia['name']}.")
                            continue
                    else:
                        print(
                            f"No se pudo obtener el CodigoArancelario de la familia padre para la subfamilia {familia['name']}.")
                        continue

                # Verificar si la familia ya existe en WooCommerce por su slug
                existing_family = wc_api.get(f"products/categories?slug={familia['slug']}")

                if existing_family.status_code == 200 and existing_family.json():
                    print(f"La familia '{familia['name']}' ya existe en WooCommerce.")
                else:
                    # Si no existe, insertar la familia
                    familia_data = familia.copy()  # Copiar los datos de la familia
                    if parent_id is not None:
                        familia_data['parent'] = parent_id  # Establecer el ID de la familia padre
                    response = wc_api.post("products/categories", familia_data)

                    if response.status_code == 201:
                        print(f"Familia '{familia['name']}' insertada con éxito.")

                        # Obtener el ID de la categoría insertada
                        familia_wooc = response.json()
                        familia_id = familia_wooc["id"]
                        parent_id = familia_wooc["parent"]

                        # Es una familia
                        if parent_id == 0:
                            cursor_sage.execute(f"UPDATE Familias SET CodigoArancelario = '{familia_id}'"
                                                f" WHERE CodigoEmpresa = 101"
                                                f" AND CodigoFamilia = '{familia['codFamilia']}' AND CodigoSubfamilia = "
                                                f"'**********'")
                            conn_sage.commit()

                        # Es una subfamilia
                        else:
                            cursor_sage.execute(f"UPDATE familias SET CodigoArancelario = '{familia_id}'"
                                                f" WHERE CodigoEmpresa = 101 AND CodigoSubfamilia = '{familia['codFamilia']}'")
                            conn_sage.commit()

                    else:
                        print(
                            f"Error al insertar la familia '{familia['name']}'. "
                            f"Código de estado: {response.status_code}")
    except Exception as e:
        print("Error al insertar las familias:", e)


# Obtiene el codigo arancelario bd sage que es el id familia de woocommerce
def obtener_codigo_arancelario(cursor, cod_familia):
    query = (f"SELECT CodigoArancelario FROM Familias WHERE CodigoEmpresa = 101 "
             f"AND CodigoFamilia = '{cod_familia}' AND CodigoSubfamilia = '**********'")
    cursor.execute(query)
    result = cursor.fetchone()
    if result:
        return result[0]
    return None


# Actualiza los nombres de las familias de Woocommerce desde Sage
def actualizar_familias(wc_api):
    # Obtener categorías de la base de datos de Sage
    familias_sage = obtener_familias_bd_actualizar()

    if not familias_sage:
        print("No se pudieron obtener las familias de Sage.")
        return

    for familia_sage in familias_sage:
        cod_arancelario_sage = familia_sage["codArancelario"]
        nombre_sage = familia_sage["name"]

        try:
            # Obtener la familia específica de WooCommerce
            familia_wooc = wc_api.get(f"products/categories/{cod_arancelario_sage}").json()

            if "name" in familia_wooc:
                nombre_wooc = familia_wooc["name"]
                # Si el nombre bd es distinto al de Woocommerce modificarlo
                if nombre_wooc != nombre_sage:
                    try:
                        familia_data = {"name": nombre_sage , "slug": nombre_sage}
                        # Actualizar nombre familia con el metodo put de la API
                        wc_api.put(f"products/categories/{cod_arancelario_sage}", familia_data).json()
                        print(f"Familia actualizada en WooCommerce: {nombre_sage}")
                    except Exception as e:
                        print(f"Error al actualizar la familia en WooCommerce: {e}")
        except Exception as e:
            print(f"Error al obtener la familia de WooCommerce con ID {cod_arancelario_sage}: {e}")


# print(obtener_familias_bd_actualizar())
# print(obtener_familias_woocommerce(get_wc_api()))
# actualizar_familias(get_wc_api())
importar_familias(get_wc_api())
# print(obtener_familias_bd_importar())

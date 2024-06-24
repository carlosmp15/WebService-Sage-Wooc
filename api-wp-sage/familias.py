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


def show_families(wc_api):
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
        print(json.dumps(all_categories, indent=4, ensure_ascii=False).encode('utf-8').decode())
        return all_categories
    except Exception as e:
        print("Error al obtener categorías:", e)
        return None


def add_families(wc_api, families):
    try:
        if not os.path.exists(families):
            print(f"Error: El archivo JSON '{families}' especificado no existe.")
            return

        with open(families, encoding='utf-8') as file:
            categories_data = json.load(file)

        if wc_api is None:
            print("Error: La conexion a la API de WooCommerce no se ha establecido correctamente.")
            return

        for category in categories_data:
            nueva_familia_creada = wc_api.post("products/categories", category)
            if nueva_familia_creada.status_code == 201:
                familia_creada_info = nueva_familia_creada.json()
                nombre_familia = familia_creada_info.get('name', '')
                id_familia = familia_creada_info.get('id', '')
                print(f"familia '{nombre_familia}' con ID {id_familia} ha sido creada.")
            else:
                print("Error al crear la familia:", nueva_familia_creada.json())
    except Exception as e:
        print("Error al agregar familias:", e)


def update_families(wc_api, nueva_familia_json):
    if not os.path.exists(nueva_familia_json):
        print("El archivo JSON especificado no existe.")
        return

    try:
        familias_disponibles = show_families(wc_api)
        if familias_disponibles:
            with open(nueva_familia_json, 'r', encoding='utf-8') as file:
                nueva_familia = json.load(file)

            familia_encontrada = False
            for familia in familias_disponibles:
                id_familia_modificar = familia['id']
                if id_familia_modificar == nueva_familia.get('id'):
                    wc_api.put(f"products/categories/{id_familia_modificar}", nueva_familia)
                    print("familia modificada con exito.")
                    familia_encontrada = True
                    break

            if not familia_encontrada:
                print("No se encontro ninguna familia para actualizar.")
    except Exception as e:
        print("Error al modificar familias:", e)


def remove_families(wc_api, familias_eliminar):
    if not os.path.exists(familias_eliminar):
        print("El archivo JSON especificado no existe.")
        return

    try:
        familias_disponibles = show_families(wc_api)
        if familias_disponibles:
            with open(familias_eliminar, 'r', encoding='utf-8') as file:
                ids_a_eliminar = json.load(file)

            # verifica si se proporcionaron IDs en el JSON
            if not ids_a_eliminar:
                print("No se proporcionaron IDs de familias en el archivo JSON.")
                return

            for id_familia_eliminar in ids_a_eliminar:
                for familia in familias_disponibles:
                    if str(familia['id']) == id_familia_eliminar:
                        response = wc_api.delete(f"products/categories/{id_familia_eliminar}?force=true")
                        if response.status_code == 200:
                            print(f"familia con ID {id_familia_eliminar} eliminada con exito.")
                        else:
                            print(f"Error al eliminar la familia con ID {id_familia_eliminar}: {response.json()}")
                        break
                else:
                    print(f"No se encontro ninguna familia con el ID {id_familia_eliminar}.")
    except Exception as e:
        print("Error al eliminar familias:", e)


def check_family(cursor, tabla, nomb_columna, valor_where):
    cursor.execute(
        "SELECT COUNT(*) FROM " + tabla + " WHERE CodigoEmpresa = 3 AND " + nomb_columna + "  = ?",
        (valor_where,))
    row = cursor.fetchone()

    return row[0] > 0


def insert_families(familias):
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

            for familia in familias:
                id_f = familia.get('id')
                nombre = familia.get('name')
                parent_id = familia.get('parent')

                # Verifica si la familia o subfamilia ya existe en la base de datos de Sage
                if int(parent_id) > 0:  # Si es una subfamilia
                    id_subfamilia = id_f
                    id_familia = parent_id
                else:  # Si es una familia
                    id_familia: str = id_f
                    id_subfamilia: str = '**********'

                # Verifica si la familia o subfamilia ya existe en la base de datos de Sage
                # "SELECT COUNT(*) FROM " + tabla + " WHERE CodigoEmpresa = 3 AND " + nomb_columna + "  = ?",
                if check_family(cursor, "Familias",
                                # Verifica en la columna de familias o subfamilias
                                "CodigoFamilia" if int(parent_id) == 0 else "CodigoSubfamilia",
                                str(id_familia if int(parent_id) == 0 else id_subfamilia)):
                    print("La familia/subfamilia " + nombre + " ya existe en la BD.")
                    continue

                cursor.execute(
                    "INSERT INTO TmpIME_Familias (CodigoEmpresa, CodigoFamilia, "
                    "CodigoSubfamilia, Descripcion, IdProcesoIME) "
                    "VALUES (?, ?, ?, ?, ?)", (3, id_familia, id_subfamilia, nombre,
                                               "00000000-0000-0000-0000-000000000001"))

                conn.commit()
                print(f"Familia/Subfamilia con ID {id_f} insertada correctamente.")

        else:
            print("No se ha establecido conexión con la BD...")

        conn.close()

    except pyodbc.Error as e:
        print("Error de SQL:", e)
    except Exception as e:
        print("Error:", e)


show_families(get_wc_api())
# add_families(get_wc_api(), "json/nueva_familia.json")
# update_families(get_wc_api(), "json/mod_familia.json")
# remove_families(get_wc_api(), "json/familias_elim.json")
# insert_families(show_families(get_wc_api()))

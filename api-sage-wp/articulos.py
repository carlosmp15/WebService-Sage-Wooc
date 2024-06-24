#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyodbc
import re
import os
import json
from PIL import Image
import hashlib
from ftplib import FTP
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


def obtener_articulos_woocommerce(wc_api):
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

        return all_products
    except Exception as e:
        print("Error al obtener productos:", e)
        return None


# Obtiene el codArancelario que es el codigo de la familia o subfamilia dependiendo
# de lo que tenga asignado el artículo, para actualizarlo a posteriori
# (Sage asigna a los artículos siempre el codArancelario de la familia no de la subfamilia)
def obtener_cod_arancelario(cod_articulo):
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta1 = (f"SELECT CodigoSubfamilia FROM Articulos WHERE CodigoEmpresa = 101"
                     f" AND CodigoArticulo = '{cod_articulo}'")

        cursor.execute(consulta1)

        # Obtener los datos seleccionados
        datos_desde_bd = cursor.fetchone()

        for subfamilia in datos_desde_bd:
            # Es una familia padre
            if subfamilia == "":
                cursor.execute("SELECT f.CodigoArancelario FROM Familias f INNER JOIN Articulos a "
                               "ON f.CodigoFamilia = a.CodigoFamilia WHERE f.CodigoEmpresa = 101 "
                               f"AND CodigoArticulo = '{cod_articulo}' AND f.CodigoSubfamilia = '**********'")
                cod_arancelario = cursor.fetchone()
            # Es una subfamilia
            else:
                cursor.execute("SELECT f.CodigoArancelario FROM Familias f INNER JOIN Articulos a "
                               "ON f.CodigoSubfamilia = a.CodigoSubfamilia WHERE f.CodigoEmpresa = 101"
                               f" AND CodigoArticulo = '{cod_articulo}'")
                cod_arancelario = cursor.fetchone()

            # Si se encontró un resultado, retornarlo
            if cod_arancelario:
                return cod_arancelario[0]

    except pyodbc.Error as e:
        print(e)
        return None


# Obtiene los artículos desde bd Sage
def obtener_articulos_bd():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta1 = ("SELECT CodigoArticulo, DescripcionArticulo, DescripcionLinea, ComentarioArticulo, "
                     "CodigoArancelario, PrecioVenta, CodigoSubfamilia, CodigoFamilia, CodigoAlternativo, lb.sysFichero "
                     "FROM Articulos a "
                     "INNER JOIN lsysBinary lb ON lb.sysIdBinario = a.ImagenExt1 "
                     "WHERE CodigoEmpresa = 101;")

        cursor.execute(consulta1)

        # Obtener los datos seleccionados
        datos_desde_bd = cursor.fetchall()

        # Convertir los datos a una lista de diccionarios
        datos_json = []
        fila_json = ""
        for fila in datos_desde_bd:
            # Sí es una familia padre
            if fila[6] == "":
                fila_json = {
                    "codAlternativo": fila[8],
                    "sku": fila[0],
                    "name": fila[1],
                    "type": "variable",
                    "description": fila[2],
                    "short_description": fila[3],
                    "categories": [
                        {
                            "id": int(fila[4]),
                        }
                    ],
                    "regular_price": str(fila[5]),
                    "src": fila[9]
                }
            # Sí es una subfamilia
            else:
                # Consulta que obtiene el Código Arancelario (id familia WooCommerce)
                # de la familia padre mediante el CodigoFamilia y CodigoSubfamilia
                consulta2 = ("SELECT CodigoArancelario FROM Familias "
                             f"WHERE CodigoFamilia = '{fila[7]}' AND CodigoSubfamilia = '{fila[6]}' "
                             f"AND CodigoEmpresa = 101 AND CodigoSubfamilia != '**********'")
                cursor.execute(consulta2)
                subfamilia = cursor.fetchall()

                for fila1 in subfamilia:
                    fila_json = {
                        "codAlternativo": fila[8],
                        "sku": fila[0],
                        "name": fila[1],
                        "type": "variable",
                        "description": fila[2],
                        "short_description": fila[3],
                        "categories": [
                            {
                                "id": int(fila[4])
                            },
                            {
                                "id": int(fila1[0])  # codigo subfamilia wooc
                            }
                        ],
                        "regular_price": str(fila[5]),
                        "src": fila[9]
                    }

            datos_json.append(fila_json)

        # Cerrar la conexión después de obtener todos los datos
        conn.close()

        return datos_json
    except pyodbc.Error as e:
        print(e)
        return None


# Obtiene nombre de los atributos desde bd Sage (tallas y colores)
def obtener_atributos_bd():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta = "SELECT DescripcionGrupoTalla_ FROM GrupoTallas_ WHERE CodigoEmpresa = 101;"

        cursor.execute(consulta)

        # Obtener los datos seleccionados
        datos_desde_bd = cursor.fetchall()

        # Convertir los datos a una lista de diccionarios
        datos_json = []
        for fila in datos_desde_bd:
            # Agregar el atributo "TALLAJE LETRAS" a la lista de diccionarios
            datos_json.append({"name": fila[0]})

        # Agregar el atributo "COLORES" a la lista de diccionarios
        datos_json.append({"name": "COLORES"})

        # Cerrar la conexión después de obtener todos los datos
        conn.close()
        return datos_json

    except pyodbc.Error as e:
        print(e)
        return None


# Obtiene los terminos de los colores desde bd Sage
def obtener_terms_colores_bd():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta = "SELECT Color_ FROM Colores_ WHERE CodigoEmpresa = 101;"

        cursor.execute(consulta)

        # Obtener los datos seleccionados
        datos_desde_bd = cursor.fetchall()

        # Convertir los datos a una lista de diccionarios
        datos_json = []
        for fila in datos_desde_bd:
            # Agregar el atributo "TALLAJE LETRAS" a la lista de diccionarios
            datos_json.append({"name": fila[0]})

        # Cerrar la conexión después de obtener todos los datos
        conn.close()
        return datos_json

    except pyodbc.Error as e:
        print(e)
        return None


# Obtiene los terminos de las tallas desde bd Sage
def obtener_terms_tallas_bd():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta = "SELECT * FROM GrupoTallas_ WHERE CodigoEmpresa = 101;"

        cursor.execute(consulta)

        # Obtener los datos seleccionados
        datos_desde_bd = cursor.fetchall()

        # Verificar si se obtuvieron datos
        if not datos_desde_bd:
            print("No se encontraron datos.")
            return None

        # Obtener el número de tallas
        numero_tallas = int(datos_desde_bd[0][3])  # Numero de tallas esta en la cuarta columna

        # Extraer las tallas
        tallas = []
        for i in range(4, 4 + (numero_tallas * 3), 3):
            talla = datos_desde_bd[0][i]
            tallas.append({"name": talla})

        # Cerrar la conexión después de obtener todos los datos
        conn.close()
        return tallas

    except pyodbc.Error as e:
        print(e)
        return None


# Obtiene los atributos de los colores asignados en los articulos
def obtener_colores_de_articulos_bd():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta = ("SELECT DISTINCT c.Color_ ,a.CodigoAlternativo FROM MovimientoStock ms "
                    "INNER JOIN Colores_ c ON ms.CodigoColor_ = c.CodigoColor_ "
                    "INNER JOIN Articulos a ON ms.CodigoArticulo = a.CodigoArticulo "
                    "WHERE ms.CodigoEmpresa = 101;")

        cursor.execute(consulta)

        datos_desde_bd = cursor.fetchall()

        datos_json = []
        for fila in datos_desde_bd:
            datos_json.append({
                "codAlternativo": fila[1],  # Id Wooc articulo
                "nombreAtrib": "COLORES",
                "name": fila[0]
            })

        conn.close()
        return datos_json

    except pyodbc.Error as e:
        print(e)
        return None


# Obtiene los atributos de las tallas asignadas en los articulos
def obtener_tallas_de_articulos_bd():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta = ("SELECT DISTINCT gt.DescripcionGrupoTalla_ ,ms.CodigoTalla01_ ,a.CodigoAlternativo "
                    "FROM MovimientoStock ms "
                    "INNER JOIN Articulos a ON ms.CodigoArticulo = a.CodigoArticulo "
                    "INNER JOIN GrupoTallas_ gt ON  ms.GrupoTalla_ = gt.GrupoTalla_ "
                    "WHERE ms.CodigoEmpresa = 101;")

        cursor.execute(consulta)

        datos_desde_bd = cursor.fetchall()

        datos_json = []
        for fila in datos_desde_bd:
            datos_json.append({
                "codAlternativo": fila[2],  # Id Wooc articulo
                "nombreAtrib": fila[0],  # Descripcion grupo talla
                "color": fila[1]
            })

        conn.close()
        return datos_json

    except pyodbc.Error as e:
        print(e)
        return None


# Obtiene el stock de los articulos de bd Sage dependiendo
# de las variaciones del artículo
def obtener_stock_variaciones_bd():
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = conn.cursor()

        consulta = ("SELECT a.CodigoAlternativo, Color_ ,CodigoTalla01_, a.PrecioVenta, acs.UnidadSaldo "
                    "FROM AcumuladoStock acs  "
                    "INNER JOIN Articulos a ON acs.CodigoArticulo = a.CodigoArticulo "
                    "INNER JOIN Colores_ c ON acs.CodigoColor_ = c.CodigoColor_ "
                    "WHERE acs.CodigoEmpresa = 101 "
                    "AND Ejercicio=year(getdate()) "
                    "AND CodigoAlmacen ='001' AND Periodo=99")

        cursor.execute(consulta)

        datos_desde_bd = cursor.fetchall()

        datos_json = []
        for fila in datos_desde_bd:
            datos_json.append({
                "codAlternativo": int(fila[0]),  # Id Wooc articulo
                "codTalla": fila[2],  # Descripcion grupo talla
                "color": fila[1],
                "unidades": str(fila[4]),
                "precio": str(fila[3])
            })

        conn.close()
        return datos_json

    except pyodbc.Error as e:
        print(e)
        return None


# Importa los atributos generales de los articulos a Woocommerce
def importar_atributos(wc_api):
    if wc_api is None:
        print("No se pudo obtener la API de WooCommerce. Verifica la conexión.")
        return

    atributos_bd = obtener_atributos_bd()
    if atributos_bd is None:
        print("No se pudo obtener los atributos de la base de datos.")
        return

    # Obtener los atributos existentes en WooCommerce
    atributos_wooc = wc_api.get('products/attributes').json()

    for atributo_bd in atributos_bd:
        # Verificar si el atributo ya existe en WooCommerce por nombre
        nombre_atributo_bd = atributo_bd['name']
        existe_en_woocomerce = any(atributo_wooc["name"] == nombre_atributo_bd for atributo_wooc in atributos_wooc)

        if existe_en_woocomerce:
            print(f'El atributo "{nombre_atributo_bd}" ya existe en WooCommerce.')
            # Obtener el ID del atributo existente
            atributo_id = next((atributo_wooc["id"] for atributo_wooc in atributos_wooc if
                                atributo_wooc["name"] == nombre_atributo_bd), None)
        else:
            # Crear el nuevo atributo en WooCommerce
            respuesta_creacion = wc_api.post('products/attributes', atributo_bd)

            if respuesta_creacion.status_code == 201:
                atributo_id = respuesta_creacion.json().get("id")
                print(f'Atributo "{nombre_atributo_bd}" creado exitosamente con ID {atributo_id}.')
            else:
                print(f'Error al crear el atributo "{nombre_atributo_bd}": {respuesta_creacion.json()}')
                continue  # Ir al siguiente atributo en caso de error

        # Verificar si el atributo es de tipo "Colores" o "Tallas"
        nombre_atributo = atributo_bd.get("name")
        if nombre_atributo == "COLORES":
            # Llamar a la función para importar términos de colores
            importar_terms(wc_api, atributo_id, obtener_terms_colores_bd())
        elif nombre_atributo == "TALLAJE  LETRAS":
            # Llamar a la función para importar términos de tallas
            importar_terms(wc_api, atributo_id, obtener_terms_tallas_bd())
        else:
            print(f'Tipo de atributo "{nombre_atributo_bd}" no compatible.')


# Importa los terminos de atributos generales en Woocommerce desde bd Sage
# id_atributo_wooc ≥ id atributo en Wooc a usar para importar los terminos
# terms_bd ≥ obtiene los datos de los terminos bd para importarlos en el atributo
def importar_terms(wc_api, id_atributo_wooc, terms_bd):
    if wc_api is None:
        print("No se pudo obtener la API de WooCommerce. Verifica la conexión.")
        return

    if terms_bd is None:
        print("No se pudieron obtener los términos de la base de datos.")
        return

    terms_wooc = wc_api.get(f'products/attributes/{id_atributo_wooc}/terms').json()

    for term in terms_bd:
        # Verificar si el término ya existe en WooCommerce por nombre
        nombre_term_bd = term['name']

        existe_en_woocomerce = any(term_wooc["name"] == nombre_term_bd for term_wooc in terms_wooc)

        if existe_en_woocomerce:
            print(f'El término "{nombre_term_bd}" ya existe en WooCommerce.')
        else:
            respuesta_creacion = wc_api.post(f'products/attributes/{id_atributo_wooc}/terms', term)

            if respuesta_creacion.status_code == 201:
                print(f'Término "{nombre_term_bd}" creado exitosamente.')
            else:
                print(f'Error al crear el término "{nombre_term_bd}": {respuesta_creacion.json()}')


def comprobar_hash(ruta_imagen, ruta_log):
    # Calcular el hash de la imagen
    with Image.open(ruta_imagen) as img:
        img_bytes = img.tobytes()
        hash_obj = hashlib.sha256()
        hash_obj.update(img_bytes)
        img_hash = hash_obj.hexdigest()

    # Leer el archivo JSON
    if os.path.exists(ruta_log) and os.path.getsize(ruta_log) > 0:
        with open(ruta_log, 'r') as log_file:
            try:
                log_data = json.load(log_file)
            except json.JSONDecodeError:
                log_data = {}
    else:
        log_data = {}

    # Verificar si el hash ya está en el registro
    if img_hash in log_data:
        return True, None
    else:
        # Si no está, añadir el hash al registro y guardar el archivo JSON
        log_data[img_hash] = ruta_imagen
        with open(ruta_log, 'w') as log_file:
            json.dump(log_data, log_file, indent=4)

        # Subir la imagen al servidor FTP y devolver la URL
        url_ftp = subida_img_ftp(ruta_imagen)
        return False, url_ftp


def subida_img_ftp(ruta_imagen):
    servidor_ftp = "ftp.server.com"
    usuario = "user"
    contras = "password"
    directorio = "/url/ftp"

    # Obtener el nombre del archivo con su extensión
    nombre_archivo = os.path.basename(ruta_imagen)

    # Construir la ruta en el servidor FTP (manteniendo el directorio deseado)
    ftp_path = f"{directorio}/{nombre_archivo}"

    with FTP(servidor_ftp) as ftp:
        ftp.login(user=usuario, passwd=contras)
        with open(ruta_imagen, 'rb') as file:
            ftp.storbinary(f'STOR {ftp_path}', file)

    # Construir la URL completa de la imagen en el servidor FTP
    return f'https://{servidor_ftp}/wp/img_sage/{nombre_archivo}'


# Importa los articulos desde bd Sage a Woocommerce
def importar_articulos(wc_api):
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)

        cursor = conn.cursor()
        articulos_bd = obtener_articulos_bd()
        if wc_api is None:
            print("No se pudo obtener la API de WooCommerce. Verifica la conexión.")
            return

        if articulos_bd is None:
            print("No se pudieron obtener los artículos de la base de datos.")
            return

        if conn:
            try:
                for articulo1 in articulos_bd:
                    # Verificar si la imagen asociada al artículo está en el servidor FTP
                    ruta_imagen = articulo1.get('src')
                    if ruta_imagen:
                        existe_en_registro, url_imagen = comprobar_hash(ruta_imagen, r'C:\ConectorWoo\log.json')
                        if not existe_en_registro and url_imagen:
                            # Si la imagen no está en el servidor FTP, subirla y obtener la URL
                            url_imagen_ftp = subida_img_ftp(ruta_imagen)
                            # Actualizar la URL de la imagen en la lista de imágenes del artículo
                            image_data = {
                                "src": url_imagen_ftp,
                            }
                            # Agregar la imagen a la lista de imágenes del artículo
                            if 'images' not in articulo1:
                                articulo1['images'] = []
                            articulo1['images'].append(image_data)

                    # Verificar si el artículo ya existe en WooCommerce por su SKU
                    existing_product = wc_api.get(f"products?sku={articulo1['sku']}")

                    # Si el producto ya existe en WooCommerce, imprimir un mensaje de error
                    if existing_product.status_code == 200 and existing_product.json():
                        print(f"El producto '{articulo1['name']}' ya existe en WooCommerce.")
                        continue  # Pasar al siguiente artículo

                    # Si no existe, insertar el producto
                    response = wc_api.post("products", articulo1)

                    if response.status_code == 201:
                        print(f"Producto '{articulo1['name']}' insertado con éxito.")

                        # Actualizar la lista de productos de WooCommerce
                        articulos_wooc = obtener_articulos_woocommerce(wc_api)

                        # Crear un diccionario para mapear los SKU a los IDs de WooCommerce
                        sku_to_id_mapping = {articulo['sku']: articulo['id'] for articulo in articulos_wooc}

                        # Iterar sobre los productos de la base de datos Sage y actualizar el CodAlternativo
                        # con el ID correspondiente de WooCommerce
                        for producto_bd in articulos_wooc:
                            sku = producto_bd['sku']
                            if sku in sku_to_id_mapping:
                                woocommerce_id = sku_to_id_mapping[sku]
                                # Actualizar el producto en la base de datos Sage con el ID de WooCommerce
                                cursor.execute(
                                    f"UPDATE Articulos SET CodigoAlternativo = '{woocommerce_id}',"
                                    f" CodigoArancelario = '{obtener_cod_arancelario(sku)}' WHERE "
                                    f"CodigoArticulo = '{sku}' AND CodigoEmpresa = 101")
                                cursor.commit()

                    else:
                        print(
                            f"Error al insertar el producto '{articulo1['name']}'. "
                            f"Código de estado: {response.status_code}")

            except Exception as e:
                print(e)

    except Exception as e:
        print(e)


# Añade los atributos de los articulos guardados
# en sage a los articulos existentes en Woocommerce
def set_atributos_articulos(wc_api):
    if wc_api is None:
        print("No se pudo obtener la API de WooCommerce. Verifica la conexión.")
        return

    colores_articulos = obtener_colores_de_articulos_bd()
    tallas_articulos = obtener_tallas_de_articulos_bd()

    if colores_articulos is None:
        print("No se pudieron obtener los colores asignados al artículo en la base de datos.")
        return
    if tallas_articulos is None:
        print("No se pudieron obtener las tallas asignadas al artículo en la base de datos.")
        return

    # Obtener todos los atributos existentes de WooCommerce
    atributos_wooc = wc_api.get('products/attributes/').json()

    # Colores asignados a artículos Sage
    for color in colores_articulos:
        id_articulo_wooc = color['codAlternativo']
        nombre_color = color['name']
        nombre_atrib = color['nombreAtrib']

        # Buscar el atributo correspondiente en WooCommerce
        atributo_existente = next((atributo for atributo in atributos_wooc if atributo["name"] == nombre_atrib), None)

        # Si existe el atributo en WooCommerce
        if atributo_existente:
            id_atrib = atributo_existente["id"]

            # Obtener los atributos actuales del producto
            producto = wc_api.get(f'products/{id_articulo_wooc}').json()

            # Buscar el atributo de color en los atributos del producto
            atributo_color = next((attr for attr in producto['attributes'] if attr['id'] == id_atrib), None)

            # Si el atributo de color ya existe en el producto, verificar opciones
            if atributo_color:
                opciones_color = atributo_color['options']
                if nombre_color not in opciones_color:
                    opciones_color.append(nombre_color)
                    # Actualizar el producto con las nuevas opciones de atributos
                    respuesta_actualizacion = wc_api.put(f'products/{id_articulo_wooc}',
                                                         {"attributes": producto['attributes']})
                    if respuesta_actualizacion.status_code == 200:
                        print(f'Atributo de color \'{nombre_color}\' añadido al artículo con id {id_articulo_wooc}')
                    else:
                        print(f'Error al añadir el atributo de color al artículo con id {id_articulo_wooc}')
                else:
                    print(
                        f'La variacion de color \'{nombre_color}\' ya está añadida al artículo con id {id_articulo_wooc}')
            else:
                # Si el atributo de color no existe en el producto, agregarlo con la nueva opción
                nuevo_atributo = {
                    "id": id_atrib,
                    "name": nombre_atrib,
                    "visible": True,
                    "variation": True,
                    "options": [nombre_color]
                }
                producto['attributes'].append(nuevo_atributo)
                # Actualizar el producto con el nuevo atributo
                respuesta_actualizacion = wc_api.put(f'products/{id_articulo_wooc}',
                                                     {"attributes": producto['attributes']})
                if respuesta_actualizacion.status_code == 200:
                    print(f'Atributo de color \'{nombre_color}\' añadido al artículo con id {id_articulo_wooc}')
                else:
                    print(f'Error al añadir el atributo de color al artículo con id {id_articulo_wooc}')
        else:
            print(f'No existe el atributo de color con nombre {nombre_atrib}')

    # Tallas asignadas a artículos Sage
    for talla in tallas_articulos:
        id_articulo_wooc = talla['codAlternativo']
        nombre_talla = talla['color']
        nombre_atrib = talla['nombreAtrib']

        # Buscar el atributo correspondiente en WooCommerce
        atributo_existente = next((atributo for atributo in atributos_wooc if atributo["name"] == nombre_atrib), None)

        # Si existe el atributo en WooCommerce
        if atributo_existente:
            id_atrib = atributo_existente["id"]

            # Obtener los atributos actuales del producto
            producto = wc_api.get(f'products/{id_articulo_wooc}').json()

            # Buscar el atributo de talla en los atributos del producto
            atributo_talla = next((attr for attr in producto['attributes'] if attr['id'] == id_atrib), None)

            # Si el atributo de talla ya existe en el producto, verificar opciones
            if atributo_talla:
                opciones_talla = atributo_talla['options']
                if nombre_talla not in opciones_talla:
                    opciones_talla.append(nombre_talla)
                    # Actualizar el producto con las nuevas opciones de atributos
                    respuesta_actualizacion = wc_api.put(f'products/{id_articulo_wooc}',
                                                         {"attributes": producto['attributes']})
                    if respuesta_actualizacion.status_code == 200:
                        print(f'Atributo de talla \'{nombre_talla}\' añadido al artículo con id {id_articulo_wooc}')
                    else:
                        print(f'Error al añadir el atributo de talla al artículo con id {id_articulo_wooc}')
                else:
                    print(
                        f'La variacion de talla \'{nombre_talla}\' ya está añadida al artículo con id {id_articulo_wooc}')
            else:
                # Si el atributo de talla no existe en el producto, agregarlo con la nueva opción
                nuevo_atributo = {
                    "id": id_atrib,
                    "name": nombre_atrib,
                    "visible": True,
                    "variation": True,
                    "options": [nombre_talla]
                }
                producto['attributes'].append(nuevo_atributo)
                # Actualizar el producto con el nuevo atributo
                respuesta_actualizacion = wc_api.put(f'products/{id_articulo_wooc}',
                                                     {"attributes": producto['attributes']})
                if respuesta_actualizacion.status_code == 200:
                    print(f'Atributo de talla \'{nombre_talla}\' añadido al artículo con id {id_articulo_wooc}')
                else:
                    print(
                        f'Error al añadir el atributo de talla \'{nombre_talla}\' al artículo con id {id_articulo_wooc}')
        else:
            print(f'No existe el atributo de talla con nombre {nombre_atrib}')


# Añade el precio y el stock de las variaciones de los articulos
# comprueba si existe la variacion y si existe modifica el stock
# y el precio siempre y cuando sean distintos
def set_precio_stock_variaciones(wc_api):
    if wc_api is None:
        print("No se pudo obtener la API de WooCommerce. Verifica la conexión.")
        return

    stock_variaciones_bd = obtener_stock_variaciones_bd()

    if stock_variaciones_bd is None:
        print("No se pudieron obtener los datos de stock y precio de las variaciones desde la base de datos.")
        return

    for variacion_bd in stock_variaciones_bd:
        id_articulo_wooc = variacion_bd['codAlternativo']

        # Obtener los atributos del producto principal
        atributos_producto = wc_api.get(f'products/{id_articulo_wooc}').json()['attributes']
        id_color = next((attr['id'] for attr in atributos_producto if attr['name'] == 'COLORES'), None)
        id_talla = next((attr['id'] for attr in atributos_producto if attr['name'] == 'TALLAJE LETRAS'), None)

        cod_talla = variacion_bd['codTalla']
        color = variacion_bd['color']
        unidades = float(variacion_bd['unidades'])
        precio = float(variacion_bd['precio'])

        # Obtener la variación existente si hay alguna
        variaciones_woocommerce = wc_api.get(f'products/{id_articulo_wooc}/variations').json()
        variacion_existente = next((var for var in variaciones_woocommerce if
                                    var['attributes'][0]['option'] == color and var['attributes'][1][
                                        'option'] == cod_talla), None)

        if variacion_existente:
            # Verificar si el precio o el stock son diferentes
            if float(variacion_existente['regular_price']) != precio or int(
                    variacion_existente['stock_quantity']) != unidades:
                # Actualizar precio y stock
                variacion_id = variacion_existente['id']
                variacion_data = {
                    "regular_price": str(precio),
                    "manage_stock": True,
                    "stock_quantity": int(unidades)
                }
                respuesta_actualizacion = wc_api.put(f'products/{id_articulo_wooc}/variations/{variacion_id}',
                                                     variacion_data)

                if respuesta_actualizacion.status_code == 200:
                    print(
                        f'Variación actualizada correctamente para el artículo {id_articulo_wooc} con talla {cod_talla} y color {color}')
                else:
                    print(
                        f'Error al actualizar la variación para el artículo {id_articulo_wooc} con talla {cod_talla} y color {color}')
                    print(f'Detalle del error: {respuesta_actualizacion.json()}')
            else:
                print(
                    f'El precio y el stock de la variación para el artículo {id_articulo_wooc} con talla {cod_talla} y color {color} son iguales. No se realiza ninguna actualización.')
        else:
            # Crear una nueva variación si no existe
            nueva_variacion_data = {
                "regular_price": str(precio),
                "manage_stock": True,
                "stock_quantity": int(unidades),
                "attributes": [
                    {
                        "id": id_color,
                        "name": "COLORES",
                        "option": color
                    },
                    {
                        "id": id_talla,
                        "name": "TALLAJE LETRAS",
                        "option": cod_talla
                    }
                ]
            }
            respuesta_creacion = wc_api.post(f'products/{id_articulo_wooc}/variations', nueva_variacion_data)

            if respuesta_creacion.status_code == 201:
                print(
                    f'Nueva variación creada para el artículo {id_articulo_wooc} con talla {cod_talla} y color {color}')
            else:
                print(
                    f'Error al crear una nueva variación para el artículo {id_articulo_wooc} con talla {cod_talla} y color {color}')
                print(f'Detalle del error: {respuesta_creacion.json()}')


def eliminar_etiquetas_html(descripcion_html):
    # Expresion regular
    etiqueta_html = re.compile(r'<.*?>')

    # Reemplazar todas las etiquetas HTML por una cadena vacía
    texto_limpio = re.sub(etiqueta_html, '', descripcion_html)

    return texto_limpio


# Actualiza los articulos modificados de Sage a Woocommerce (nombre, slug, precio,
# descripcion línea, comentario artículo)
def actualizar_articulos(wc_api):
    server = '127.0.0.1'
    database = 'DB'
    username = 'user'
    password = 'password'

    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)

        cursor = conn.cursor()
        # Obtener artículos de la base de datos de Sage
        articulos_sage = obtener_articulos_bd()

        if not articulos_sage:
            print("No se pudieron obtener los artículos de Sage.")
            print("No se pudieron obtener los artículos de Sage.")
            return

        for articulo_sage in articulos_sage:
            # Codigo alternativo en Sage = id articulo Woocommerce
            cod_articulo_sage = int(articulo_sage["codAlternativo"])
            nombre_sage = articulo_sage["name"]
            precio_sage = articulo_sage["regular_price"]
            descripcion_sage = articulo_sage["description"]
            descripcion_corta_sage = articulo_sage["short_description"]

            try:
                # Obtener el artículo específico de WooCommerce
                response = wc_api.get(f"products/{cod_articulo_sage}")

                if response.status_code == 200:
                    articulo_wooc = response.json()
                else:
                    print(f"El producto con ID {cod_articulo_sage} no existe en WooCommerce.")
                    continue  # Pasar al siguiente artículo

                id_subfamilia_bd = obtener_cod_arancelario(articulo_sage["sku"])
                # Obtiene el id familia padre Woocommerce que tenga subfamilia
                cursor.execute(
                    "SELECT CodigoArancelario FROM Familias WHERE CodigoSubfamilia = '**********'  "
                    "AND CodigoEmpresa = 101 AND CodigoArancelario = ("
                    "    SELECT CodigoArancelario FROM Familias WHERE CodigoFamilia = ("
                    "        SELECT CodigoFamilia FROM Familias "
                    f"        WHERE CodigoArancelario = '{id_subfamilia_bd}' AND CodigoEmpresa = 101"
                    "    ) AND CodigoSubfamilia = '**********' AND CodigoEmpresa = 101"
                    ")"
                )

                id_familia_bd = cursor.fetchone()
                id_familia_bd = id_familia_bd[0]

                id_wooc = articulo_wooc.get("id")
                nombre_wooc = articulo_wooc.get("name")
                precio_wooc = articulo_wooc.get("regular_price")
                descripcion_wooc = eliminar_etiquetas_html(articulo_wooc.get("description"))
                descripcion_corta_wooc = eliminar_etiquetas_html(articulo_wooc.get("short_description"))
                familias_wooc = articulo_wooc.get("categories")
                id_familia_wooc = familias_wooc[0].get("id")

                # Si hay mas de dos elementos es una subfamilia porque tiene familia padre
                if len(familias_wooc) >= 2:
                    id_subfamilia_wooc = familias_wooc[1].get("id")
                else:
                    id_subfamilia_wooc = 0

                # Si el nombre o el precio son diferentes, actualizarlos
                if (id_wooc == cod_articulo_sage and nombre_wooc != nombre_sage or precio_wooc != precio_sage or
                        descripcion_wooc != descripcion_sage or descripcion_corta_wooc != descripcion_corta_sage or
                        id_familia_wooc != id_familia_bd and id_subfamilia_wooc != id_subfamilia_bd):

                    try:
                        articulo_data = {
                            "name": nombre_sage, "slug": nombre_sage.replace(" ", "-").lower(),
                            "regular_price": precio_sage, "description": descripcion_sage,
                            "short_description": descripcion_corta_sage,
                            "categories": [
                                {
                                    "id": id_familia_bd
                                },
                                {
                                    "id": id_subfamilia_bd
                                }
                            ]
                        }
                        # Actualizar nombre y precio del artículo con el método put de la API
                        response_put = wc_api.put(f"products/{cod_articulo_sage}", articulo_data)
                        if response_put.status_code == 200:
                            print(f"Artículo actualizado en WooCommerce: {nombre_sage}")
                        else:
                            print(
                                f"Error al actualizar el artículo en WooCommerce. Código de estado: {response_put.status_code}")
                    except Exception as e:
                        print(f"Error al actualizar el artículo en WooCommerce: {e}")
            except Exception as e:
                print(f"Error al obtener el artículo de WooCommerce con ID {cod_articulo_sage}: {e}")
    except Exception as e:
        print(e)


# print(obtener_articulos_bd())
# print(obtener_cod_arancelario('ADDMONT'))
print(obtener_articulos_woocommerce(get_wc_api()))
# print(obtener_atributos_bd())
# print(obtener_terms_colores_bd())
# print(obtener_terms_tallas_bd())
# print(obtener_colores_de_articulos_bd())
# print(obtener_tallas_de_articulos_bd())
# print(obtener_stock_variaciones_bd())
# importar_articulos(get_wc_api())
# actualizar_articulos(get_wc_api())
# importar_atributos(get_wc_api())
# set_atributos_articulos(get_wc_api())
# set_precio_stock_variaciones(get_wc_api())

from familias import actualizar_familias
from familias import get_wc_api
from articulos import actualizar_articulos
from clientes import actualizar_clientes

from familias import importar_familias
from articulos import importar_articulos
from clientes import importar_clientes


def actualizacion_masv():
    while True:

        importar_familias(get_wc_api())
        importar_articulos(get_wc_api())
        importar_clientes(get_wc_api())

        actualizar_familias(get_wc_api())
        actualizar_articulos(get_wc_api())
        actualizar_clientes(get_wc_api())


actualizacion_masv()

"""Herramientas de ROMs: DAT, identificacion, renombrado y formatos.

Este paquete es puro Python de la biblioteca estandar, como el resto del
manager. Vive aparte de ``app.py`` porque ya no cabe dentro: son cuatro
temas que se pueden probar por separado.

    dats      de donde salen los DAT, como se descargan y como se indexan
    identify  hashes, firmas de disco y heuristicas de titulo
    faltantes que otras versiones hay de los juegos que ya tienes
    library   el inventario de la biblioteca, los duplicados y la auditoria
    naming    las convenciones de set y como se compone un nombre
    sets      que variante es la buena cuando hay varias
    rename    el plan de renombrado, su ejecucion y la vuelta atras
    formats   deteccion, conversion, compresion y parcheo
    progress  la cuenta de lo que lleva hecho un trabajo largo
    jobs      los trabajos en segundo plano, con su progreso

La inspiracion viene del proyecto OpenROM (https://github.com/M5Devs/OpenROM),
que es GPL v3: aqui no se ha copiado su codigo, solo se han reaprovechado
ideas (deteccion por magia de cabecera, puntuacion de variantes, renombrado
segundo la convencion) y sus fuentes de datos.
"""

from . import dats, faltantes, formats, identify, jobs, library, naming, progress, rename, sets

__all__ = ["dats", "faltantes", "formats", "identify", "jobs", "library", "naming",
           "progress", "rename", "sets"]
__version__ = "1.0"

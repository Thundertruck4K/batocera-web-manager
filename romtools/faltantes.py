"""Lo que falta: las otras versiones de los juegos que ya tienes.

El DAT de un sistema es la lista de todos los juegos de ese sistema con el
nombre y el tamano de cada fichero. Comparado con la biblioteca dice dos
cosas: lo que tienes y lo que te falta.

Pero comparar "todo contra todo" no sirve de nada: el DAT de PlayStation 2
tiene 13.618 juegos y una biblioteca normal tiene 300. Decir "te faltan
13.300 juegos" no informa de nada.

Lo que si informa es lo contrario: **de los juegos que ya tienes, que otras
versiones hay**. Si tienes "Super Mario 64 (Japan)" y el DAT tiene tambien la
americana y la europea, quiza te interesa la americana. Y si el juego tiene
tres discos y solo tienes el primero, ese disco si falta de verdad.

Por eso aqui no se lista lo que falta del todo, sino **las variantes de los
juegos que tienes**: el dato es util porque el juego ya te interesa.

Nada de esto borra ni escribe nada: es solo informacion. Cada coincidencia
dice **como** se ha emparejado (nombre, hash, codigo de juego, serial o
titulo), porque una coincidencia por nombre no es lo mismo que una por hash.

La comparacion es **por sistema**: cargar los 17 indices a la vez son 55 MB
de JSON (el de scummvm son 18 MB solo) y en la consola se convierten en
varios cientos de MB de objetos de Python. Una vez fue un `oom-kill` por un
indice de 2,1 GB, y no se va a repetir.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from . import dats
from . import sets
from .identify import bare_title, identify, normalize_title, region_of, title_similarity
from .library import recolectar
from .progress import Progress

#: Presupuesto de bytes para hashear dentro de un mismo sistema. Lo que se
#: queda fuera se empareja por el nombre o por el titulo, y se dice.
PRESUPUESTO_HASH = 512 * 1024 * 1024

#: A partir de esta similitud del titulo **pelado** (sin etiquetas) se cree que
#: el fichero es esa variante del DAT. Ademas, el fichero tiene que declarar la
#: misma region o revision (`_misma_variante`): el parecido entre caracteres
#: favorece al nombre con **menos** etiquetas, asi que un fichero sin region se
#: parece mas a «Juego (USA)» (0,881) que a «Juego (Japan)» (0,758), y sin esa
#: regla se afirmaria una variante que no se sabe.
UMBRAL_EXACTO = 0.85

#: A partir de esta similitud del titulo pelado se cree que es el mismo
#: juego, aunque no se sepa que variante: eso es lo que va a «quizas». Por
#: debajo, es otro juego (una traduccion o un mod), que no sale en el DAT.
UMBRAL_TITULO = 0.80

#: Cuantos juegos se devuelven como mucho (el detalle es largo).
TOPE_GRUPOS = 400

#: Extensiones del volcado de un juego que vive dentro de una carpeta (Wii,
#: PlayStation, ScummVM...). Es lo que se identifica: el fichero de dentro.
_DUMP = (".wbfs", ".wia", ".iso", ".bin", ".cue", ".gcm", ".pbp", ".mds",
         ".mdf", ".img", ".ecm")

#: Etiqueta de idioma: ``(En,Fr,De)``.
_IDIOMA_RE = re.compile(r"^[A-Za-z]{2}(,[A-Za-z]{2})*$")
#: Etiqueta de revision: ``(Rev 2)``.
_REV_RE = re.compile(r"^(?:rev|revision)\s*(\d+)$", re.I)
#: Las etiquetas: las de parentesis ``(USA)`` y las marcas de volcado ``[!]``.
_TAG_RE = re.compile(r"\([^()]*\)|\[[^\[\]]*\]")


def _nombre(entry: dict) -> str:
    """El nombre de una entrada del DAT."""
    entry = entry or {}
    return entry.get("name") or entry.get("description") or ""


def _titulo(nombre: str) -> str:
    """El nombre del juego sin etiquetas: ``Game (USA) (Disc 1)`` -> ``Game``."""
    limpio = _TAG_RE.sub(" ", nombre or "")
    return re.sub(r"\s{2,}", " ", limpio).strip()


def _clave_sin_disco(nombre: str) -> str:
    """La identidad del juego sin ninguna etiqueta.

    ``sets.game_key()`` deja fuera la region y la revision pero **conserva** la
    etiqueta de disco, porque para renombrar el disco es parte de la
    identidad. Aqui hace falta lo contrario: "Juego (Disc 1)" y "Juego (Disc
    2)" son el mismo juego con dos discos, y hay que poder decir que falta el
    segundo. Tambien se quitan las marcas de volcado (``[b]``, ``[!]``): son
    del mismo juego, solo que con datos malos o verificados.
    """
    return normalize_title(_TAG_RE.sub(" ", nombre or ""))


def _firma(nombre: str) -> tuple:
    """La region y la revision que declara un nombre.

    ``Juego (USA) (Rev 2)`` -> ``("USA", "2")``. Lo que no dice, no se
    inventa: la region vacia es «no lo se».
    """
    return (region_of(nombre), _revision(sets.tags_of(nombre)))


def _misma_variante(nombre_fichero: str, nombre_dat: str) -> bool:
    """Si se puede afirmar que el fichero es esa variante del DAT.

    Se puede cuando los dos dicen lo mismo:

    - Los dos declaran region: tienen que ser la misma.
    - Solo uno la declara: **no se puede** (el juego es el mismo, la variante
      no se sabe). «Super Mario 64» frente a «Super Mario 64 (USA)».
    - Ninguno declara region: se puede, porque no hay nada que contradecir
      («Myst.scummvm» frente a «Myst (1993) (Windows)»).

    Con la revision pasa lo mismo: si solo uno la declara, no se afirma.
    """
    region_f, rev_f = _firma(nombre_fichero)
    region_d, rev_d = _firma(nombre_dat)
    if bool(region_f) != bool(region_d):
        # Solo uno de los dos dice su region: no se puede saber.
        return False
    if region_f and region_f != region_d:
        return False
    if bool(rev_f) != bool(rev_d):
        return False
    if rev_f and rev_f != rev_d:
        return False
    return True


def _mismo_juego(nombre_fichero: str, nombre_dat: str) -> bool:
    """Si el fichero y la entrada del DAT son el mismo juego.

    No basta con que los nombres se parezcan: «Tomb Raider  I» y «Tomb Raider
    (USA)» se parecen mucho sin las etiquetas, pero son juegos distintos.
    Sin las etiquetas los dos nombres tienen que ser el mismo.
    """
    return _clave_sin_disco(nombre_fichero) == _clave_sin_disco(nombre_dat)


def _revision(tags) -> str:
    """El numero de revision de unas etiquetas (``(Rev 2)`` -> ``2``)."""
    for tag in tags:
        match = _REV_RE.match((tag or "").strip())
        if match:
            return match.group(1)
    return ""


def _idiomas(tags) -> frozenset:
    """Los codigos de idioma de unas etiquetas (``(En,Fr,De)``)."""
    for tag in tags:
        limpio = (tag or "").replace(" ", "")
        if _IDIOMA_RE.match(limpio):
            return frozenset(limpio.split(","))
    return frozenset()


def _diferencia(falta: str, tienes: str) -> tuple:
    """Por que la version que falta es distinta de la que tienes.

    Devuelve el **codigo** del motivo y su detalle. El codigo lo traduce la
    interfaz: el backend va sin acentos, a proposito, para que el mismo texto
    se lea bien en cualquier consola.
    """
    tags_f = sets.tags_of(falta)
    tags_t = sets.tags_of(tienes)
    disco_f = sets.disc_number(falta)
    disco_t = sets.disc_number(tienes)
    if disco_f and disco_f != disco_t:
        return "disco", str(disco_f)
    region_f = region_of(falta)
    region_t = region_of(tienes)
    if region_f and region_t and region_f != region_t:
        return "region", region_f
    rev_f = _revision(tags_f)
    rev_t = _revision(tags_t)
    if rev_f and rev_t and rev_f != rev_t:
        return "revision", rev_f
    # El idioma solo cuenta si los dos lo dicen: si uno no lo tiene, lo que
    # cambia es la edicion ("(GameCube)", "(Wii Virtual Console)").
    idiomas_f = _idiomas(tags_f)
    idiomas_t = _idiomas(tags_t)
    if idiomas_f and idiomas_t and idiomas_f != idiomas_t:
        return "idioma", ", ".join(sorted(idiomas_f))
    return "version", ""


def _mejor_variante(grupo, nombre: str) -> tuple:
    """La variante del grupo que mas se parece al nombre del fichero.

    La comparacion es con el nombre **completo** (con la region y la
    revision), no con el titulo pelado: si el fichero se llama "Juego
    (Japan)", esa es la variante que tiene, no la "(USA)" que tambien esta en
    el DAT.

    Devuelve tres cosas: la variante, lo que se parece el nombre completo y
    lo que se parece el titulo pelado (que dice si es el mismo juego).
    """
    mejor = None
    mejor_score = 0.0
    mejor_clave = (-1.0, -1.0)
    mejor_pelado = 0.0
    region_f = _firma(nombre)[0]
    for entrada in grupo or []:
        nombre_dat = _nombre(entrada)
        score = title_similarity(nombre, nombre_dat)
        pelado = title_similarity(bare_title(nombre), bare_title(nombre_dat))
        region_d = _firma(nombre_dat)[0]
        # La region que declara el fichero va por delante: si dice «(USA)»,
        # la variante buena es la «(USA)», aunque su nombre sea mas corto (el
        # parecido entre caracteres favorece al que tiene menos etiquetas).
        coincide = 1.0 if (region_f and region_d and region_f == region_d) else 0.0
        clave = (coincide, score)
        if clave > mejor_clave:
            mejor_clave = clave
            mejor_score = score
            mejor = entrada
        if pelado > mejor_pelado:
            mejor_pelado = pelado
    return mejor, mejor_score, mejor_pelado


def _nombre_de_carpeta(nombre: str, exts) -> str:
    """El nombre del juego, sin la extension de la carpeta.

    ScummVM guarda cada juego en una carpeta con la extension del motor
    («Myst.scummvm») y el DAT lo llama «Myst (1993) (Windows)»: sin quitar la
    extension, la clave del juego no coincide con la de la entrada y no se
    empareja nada.
    """
    sufijo = Path(nombre).suffix
    if sufijo and sufijo.lower() in (exts or set()):
        return Path(nombre).stem
    return nombre


def _ruta_de_identificacion(base: str, sistema: str, juego, exts=None) -> tuple:
    """La ruta con la que se identifica el juego, si se puede hashear y el
    nombre con el que se compara con los nombres del DAT.

    En los juegos que viven en una carpeta (Wii, ScummVM) se identifica el
    **fichero de dentro**, que es donde esta el codigo de juego que cruza con
    el DAT. Para comparar con los nombres del DAT se usa el **nombre de la
    carpeta**: es lo que el usuario ve y lo que apunta el `gamelist.xml`.

    En un fichero suelto se compara con el nombre **sin extension**: el DAT
    nombra «Juego (USA)» y el fichero es «Juego (USA).bin». Con la extension la
    puntuacion bajaba y emparejamientos seguros acababan como dudosos.
    """
    carpeta = Path(base) / sistema / juego.nombre
    if not juego.carpeta:
        return str(carpeta), True, Path(carpeta).stem
    nombre = _nombre_de_carpeta(juego.nombre, exts)
    try:
        for hijo in sorted(carpeta.iterdir()):
            if hijo.is_file() and hijo.suffix.lower() in _DUMP:
                return str(hijo), True, nombre
    except OSError:
        pass
    return str(carpeta), False, nombre


def sistemas_con_dat(cache_dir: str) -> list:
    """Los sistemas que tienen DAT instalado y cuantos juegos tiene cada uno.

    Solo se leen los ficheros de metadatos, que son diminutos: el indice
    entero de un sistema grande pesa 18 MB y aqui no hace falta.
    """
    salida = []
    for info in dats.dat_files(cache_dir):
        salida.append({
            "sistema": info.get("system"),
            "juegos_dat": info.get("games") or 0,
            "dat": info.get("dat"),
            "fuente": info.get("source"),
            "version": info.get("version"),
        })
    salida.sort(key=lambda x: x["sistema"] or "")
    return salida


def faltantes(base: str, sistema: str, exts, cache_dir: str,
              hash_budget: int = PRESUPUESTO_HASH, progreso=None) -> dict:
    """Las versiones de los juegos que tienes que no tienes.

    ``exts`` son las extensiones que son juego en ese sistema.

    **Ojo con el progreso**: `Progress.completar()` marca el trabajo como
    terminado, asi que se llama **una sola vez**, al final. Entre fases se
    usa `reiniciar()`.
    """
    indice = dats.load_index(sistema, cache_dir)
    if indice is None:
        return {"ok": False, "error": "no hay DAT instalado para este sistema"}
    juegos_dat = indice.get("juegos")
    if not isinstance(juegos_dat, list):
        juegos_dat = []
    if not juegos_dat:
        return {"ok": False, "error": "el DAT de este sistema esta vacio"}

    prog = Progress(1, "leyendo el DAT", notificar=progreso)
    prog.avisar()

    datos = recolectar(base, [sistema], {sistema: exts})
    juegos = datos["juegos"]

    # 1 · Los grupos del DAT: un grupo es el juego con todas sus variantes
    #     (otras regiones, otras revisiones, otros discos).
    grupos_por_clave: dict = {}
    for entrada in juegos_dat:
        grupos_por_clave.setdefault(_clave_sin_disco(_nombre(entrada)), []).append(entrada)

    # 2 · Que entrada del DAT corresponde a cada juego de la biblioteca.
    prog.reiniciar(len(juegos), "emparejando con el DAT")
    emparejados = []
    probables = []
    restante = hash_budget
    for indice_juego, juego in enumerate(juegos):
        ruta, es_fichero, nombre_variante = _ruta_de_identificacion(base, sistema, juego, exts)
        try:
            tamano = os.path.getsize(ruta)
        except OSError:
            tamano = juego.tamano
        prog.empezar(juego.nombre, tamano, hechos=indice_juego)
        # El hash obliga a leer el fichero entero: con una ISO de 4 GB eso es
        # eterno, asi que va con presupuesto.
        hashear = es_fichero and tamano > 0 and tamano <= restante
        if hashear:
            restante -= tamano
        try:
            match = identify(ruta, indice,
                             title_hint=Path(juego.nombre).stem,
                             hash_allowed=hashear, on_bytes=prog.leidos)
        except OSError:
            match = None
        if match is None or not match.entry:
            continue
        grupo = grupos_por_clave.get(_clave_sin_disco(_nombre(match.entry))) or []
        if match.method != "titulo":
            # Nombre, hash, serial o codigo de juego: la coincidencia es segura.
            emparejados.append({
                "entrada": match.entry,
                "fichero": juego.nombre,
                "metodo": match.method,
                "confianza": round(match.confidence, 3),
            })
            continue
        # Por titulo: hay que comprobar que sea la MISMA variante. El titulo
        # pelado dice el juego, pero la region y la revision dicen la
        # variante, y aqui importa cual tienes.
        entrada, score, pelado = _mejor_variante(grupo, nombre_variante)
        if entrada is None:
            entrada = match.entry
        mismo = _mismo_juego(nombre_variante, _nombre(entrada))
        # Las dos reglas: el **juego** (los titulos pelados tienen que ser el
        # mismo) y la **variante** (la region que declara el nombre tiene que
        # ser la misma). Sin las dos no se afirma nada.
        if (mismo and pelado >= UMBRAL_EXACTO
                and _misma_variante(nombre_variante, _nombre(entrada))):
            emparejados.append({
                "entrada": entrada,
                "fichero": juego.nombre,
                "metodo": "titulo",
                "confianza": round(score, 3),
            })
        elif mismo and pelado >= UMBRAL_TITULO:
            # El juego es el mismo pero no se sabe que variante: no se afirma
            # ni que lo tienes ni que te falta.
            probables.append({
                "entrada": entrada,
                "fichero": juego.nombre,
                "score": round(score, 3),
            })
        # Si no es el mismo juego (un mod, una traduccion o un juego con un
        # nombre parecido), no se empareja con nada y contara como "sin DAT".

    # 3 · Los grupos de los juegos que tienes.
    por_clave: dict = {}
    for item in emparejados:
        por_clave.setdefault(_clave_sin_disco(_nombre(item["entrada"])), []).append(item)

    # Las coincidencias dudosas: pueden ser juegos que ya tienes.
    probables_por_nombre = {}
    for probable in probables:
        probables_por_nombre[_nombre(probable["entrada"])] = probable

    # 4 · Cada grupo: lo que tienes, lo que quiza tienes y lo que falta.
    detalle = []
    total_faltantes = 0
    total_mejores = 0
    grupos_con_discos = 0
    grupos_con_mejores = 0
    for clave, entradas in grupos_por_clave.items():
        presentes = por_clave.get(clave) or []
        if not presentes:
            # Solo hay coincidencias dudosas: no se afirma nada.
            continue
        nombres_presentes = {_nombre(p["entrada"]) for p in presentes}
        faltan = []
        for entrada in entradas:
            nombre = _nombre(entrada)
            if nombre in nombres_presentes:
                continue
            if nombre in probables_por_nombre:
                # Quiza ya lo tienes (coincidencia dudosa): no se afirma que
                # falte, porque no se sabe.
                continue
            faltan.append(entrada)
        if not faltan:
            continue
        mejor_tuyo = None
        for p in presentes:
            score = sets.score_entry(p["entrada"])
            if mejor_tuyo is None or score.total > mejor_tuyo.total:
                mejor_tuyo = score
        variantes = []
        for p in presentes:
            variantes.append({
                "nombre": _nombre(p["entrada"]),
                "fichero": p["fichero"],
                "metodo": p["metodo"],
                "confianza": p["confianza"],
            })
        # El DAT a veces trae dos entradas con el mismo nombre (dos volcados
        # con distinto checksum): se agrupan para no ensuciar la lista.
        por_nombre: dict = {}
        for entrada in faltan:
            por_nombre.setdefault(_nombre(entrada), []).append(entrada)
        faltan = [v[0] for v in por_nombre.values()]

        faltan_detalle = []
        for entrada in faltan:
            nombre = _nombre(entrada)
            motivo, detalle_motivo = "version", ""
            for p in presentes:
                motivo, detalle_motivo = _diferencia(nombre, _nombre(p["entrada"]))
                if motivo != "version":
                    break
            score = sets.score_entry(entrada)
            mejor = bool(mejor_tuyo is not None and score.total > mejor_tuyo.total)
            if mejor:
                total_mejores += 1
            faltan_detalle.append({
                "nombre": nombre,
                "motivo": motivo,
                "detalle": detalle_motivo,
                "mejor": mejor,
                "puntuacion": round(score.total, 2),
                # Cuantos volcados distintos hay con ese nombre en el DAT.
                "copias": len(por_nombre.get(nombre) or []),
            })
        total_faltantes += len(faltan_detalle)
        if any(f["mejor"] for f in faltan_detalle):
            grupos_con_mejores += 1

        # Los discos que faltan se cuentan como conjunto: si tienes el 1 y el
        # 3, faltan el 2 aunque el DAT no lo traiga.
        discos_dat = {sets.disc_number(_nombre(e)) for e in entradas}
        discos_dat.discard(None)
        discos_tienes = {sets.disc_number(_nombre(p["entrada"])) for p in presentes}
        discos_tienes.discard(None)
        faltan_discos = sorted(discos_dat - discos_tienes)
        if faltan_discos:
            grupos_con_discos += 1

        detalle.append({
            "titulo": _titulo(_nombre(entradas[0])),
            "variantes": variantes,
            "faltan": faltan_detalle,
            "discos_faltantes": faltan_discos,
        })

    # Los que mandan: los que faltan discos y los que tienen una version
    # mejor. Lo demas, por orden alfabetico.
    detalle.sort(key=lambda g: (-len(g["discos_faltantes"]),
                                 -sum(1 for f in g["faltan"] if f["mejor"]),
                                 g["titulo"]))

    # Los que no salen en el DAT: ni emparejados ni dudosos. Los dudosos van
    # aparte, porque de ellos no se puede decir que falten: quiza ya estan.
    nombres_emparejados = {item["fichero"] for item in emparejados}
    nombres_probables = {item["fichero"] for item in probables}
    sin_dat = [{"fichero": j.nombre, "tamano": j.tamano}
               for j in juegos if j.nombre not in nombres_emparejados
               and j.nombre not in nombres_probables]

    prog.completar()
    return {
        "ok": True,
        "sistema": sistema,
        "juegos_dat": len(juegos_dat),
        "juegos_biblioteca": len(juegos),
        "encontrados": len(emparejados),
        "sin_dat": len(sin_dat),
        "quizas": len(probables),
        "quizas_lista": [{"fichero": p["fichero"],
                          "candidato": _nombre(p["entrada"]),
                          "puntuacion": p["score"]}
                         for p in probables[:100]],
        "grupos": len(detalle),
        "grupos_mejores": grupos_con_mejores,
        "faltantes": total_faltantes,
        "mejores": total_mejores,
        "discos": grupos_con_discos,
        "detalle": detalle[:TOPE_GRUPOS],
        "detalle_recortado": len(detalle) > TOPE_GRUPOS,
        "sin_dat_lista": sin_dat[:100],
        "hasheado": restante != hash_budget,
    }

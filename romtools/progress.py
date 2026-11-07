"""Progreso de los trabajos largos.

Calcular el plan de renombrado de un sistema grande tarda: hay que
identificar miles de ficheros y algunos se hashean enteros (una ISO de 4 GB
en una tarjeta SD). Si la aplicacion solo espera en silencio, parece que se
ha quedado colgada y el usuario cierra la ventana.

Este modulo lleva la cuenta de lo que se ha hecho para que se pueda ir
enseñando mientras el trabajo dura.

El progreso se cuenta por ficheros, pero **dentro** de un fichero se cuenta
por bytes leidos: hashear una ISO es un solo fichero y se lleva el 90 % del
tiempo, asi que si solo se contaran ficheros la barra se quedaria parada
justo en lo que mas tarda.
"""

from __future__ import annotations

import threading

#: Cada cuantos bytes se avisa del avance de un fichero. Escribir en el
#: estado del trabajo en cada bloque de 1 MB seria tirar CPU para nada.
AVISO_BYTES = 8 * 1024 * 1024


class Progress:
    """Contador de progreso de un trabajo largo.

    Se puede usar desde varios hilos: el plan corre en un hilo aparte del
    que pregunta por su estado.

    El progreso va asi: ``hechos`` son los ficheros ya terminados y el
    fichero que se esta leyendo cuenta a medias (se llama ``empezar`` con
    cuantos hay hechos y el se va moviendo con ``leidos``).
    """

    def __init__(self, total: int = 0, mensaje: str = "",
                 notificar=None):
        # RLock y no Lock: ``estado`` se llama desde dentro de ``leidos``.
        self._lock = threading.RLock()
        self._notificar = notificar
        self.total = max(0, int(total or 0))
        self.hechos = 0
        self.actual = ""
        self.mensaje = mensaje
        self._bytes = 0
        self._bytes_total = 0
        self._terminado = False
        self._ultimo_aviso = 0
        self._ultimo_porcentaje = 0

    # ── Avances ──────────────────────────────────────────────────────────

    def reiniciar(self, total: int = 0, mensaje: str = "") -> None:
        """Empieza otra fase con su propio total (por ejemplo, renombrar)."""
        with self._lock:
            self.total = max(0, int(total or 0))
            self.hechos = 0
            self.actual = ""
            self._bytes = 0
            self._bytes_total = 0
            self._terminado = False
            self._ultimo_aviso = 0
            self._ultimo_porcentaje = 0
            if mensaje:
                self.mensaje = mensaje
        self._avisar()

    def empezar(self, nombre: str, tamano: int = 0, hechos=None) -> None:
        """Empieza un fichero: se esta leyendo o identificando.

        ``hechos`` son los ficheros que ya se han terminado (el que empieza
        va a medias, asi que todavia no cuenta).
        """
        with self._lock:
            if hechos is not None:
                self.hechos = max(0, int(hechos or 0))
            self.actual = nombre or ""
            self._bytes = 0
            self._bytes_total = max(0, int(tamano or 0))
            self._ultimo_aviso = 0
            self._ultimo_porcentaje = int(round(self._fraccion() * 100))
        self._avisar()

    def leidos(self, n: int) -> None:
        """Avisa de que se han leido ``n`` bytes del fichero actual."""
        with self._lock:
            self._bytes += max(0, int(n or 0))
            if self._bytes_total:
                self._bytes = min(self._bytes, self._bytes_total)
            porcentaje = int(round(self._fraccion() * 100))
            # Se avisa cuando el porcentaje cambia o cada muchos bytes: no
            # hace falta escribir el estado en cada bloque de 1 MB.
            avisar = (porcentaje > self._ultimo_porcentaje or
                      self._bytes - self._ultimo_aviso >= AVISO_BYTES)
            if avisar:
                self._ultimo_aviso = self._bytes
                self._ultimo_porcentaje = porcentaje
        if avisar:
            self._avisar()

    def completar(self) -> None:
        """Marca el trabajo como terminado."""
        with self._lock:
            self._terminado = True
            self.hechos = self.total
            self.actual = ""
            self._bytes = 0
            self._bytes_total = 0
        self._avisar()

    def avisar(self) -> None:
        """Envia el estado actual (para que se vea cuanto antes)."""
        self._avisar()

    # ── Estado ──────────────────────────────────────────────────────────

    def fraccion(self) -> float:
        """Lo que va, de 0 a 1."""
        with self._lock:
            return self._fraccion()

    def estado(self) -> dict:
        """El estado, tal y como se lo enseña a la aplicacion."""
        with self._lock:
            fraccion = self._fraccion()
            return {
                "hechos": self.hechos,
                "total": self.total,
                "actual": self.actual,
                "porcentaje": int(round(fraccion * 100)),
                "mensaje": self.mensaje,
                "terminado": self._terminado,
            }

    # ── Interno ─────────────────────────────────────────────────────────

    def _fraccion(self) -> float:
        if self._terminado:
            return 1.0
        if not self.total:
            return 0.0
        base = min(self.hechos, self.total)
        extra = 0.0
        if self._bytes_total:
            extra = min(1.0, self._bytes / self._bytes_total)
        return max(0.0, min(1.0, (base + extra) / self.total))

    def _avisar(self) -> None:
        if not self._notificar:
            return
        try:
            self._notificar(self.estado())
        except Exception:
            # Un fallo avisando del progreso no puede tumbar el trabajo.
            pass

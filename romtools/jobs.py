"""Trabajos en segundo plano, con progreso.

Algunas cosas tardan mucho (el plan de renombrado de un sistema con miles de
juegos, la conversion de un CHD de 4 GB). Si el servidor las sirve en el
hilo de la peticion, la pagina se queda esperando sin dar ninguna señal y
parece que la aplicacion se ha colgado.

Aqui se resuelve asi: la peticion arranca un **trabajo** en un hilo aparte y
devuelve su identificador; el cliente va preguntando cada poco por el
estado (cuanto lleva, que esta haciendo, que porcentaje) y cuando el
trabajo acaba, recoge el resultado.

El trabajo vive solo mientras el proceso: si el manager se reinicia, los
trabajos se pierden, que es lo que se quiere (no queda nada a medias).
"""

from __future__ import annotations

import threading
import time
import traceback
import uuid


class Job:
    """Un trabajo en curso o ya terminado."""

    def __init__(self, tipo: str, mensaje: str = ""):
        self.id = uuid.uuid4().hex[:12]
        self.tipo = tipo
        self.estado = "trabajando"       # trabajando | listo | error
        self.hechos = 0
        self.total = 0
        self.actual = ""
        self.porcentaje = 0
        self.mensaje = mensaje
        self.resultado = None
        self.error = ""
        self.iniciado = time.time()
        self.fin = None
        self._lock = threading.Lock()

    # ── Avances ──────────────────────────────────────────────────────────

    def progreso(self, estado: dict) -> None:
        """Guarda el estado que le pasa el trabajo."""
        if not isinstance(estado, dict):
            return
        with self._lock:
            self.hechos = int(estado.get("hechos", self.hechos) or 0)
            self.total = int(estado.get("total", self.total) or 0)
            self.actual = str(estado.get("actual", self.actual) or "")
            self.porcentaje = int(estado.get("porcentaje", self.porcentaje) or 0)
            self.mensaje = str(estado.get("mensaje", self.mensaje) or "")
            if estado.get("terminado"):
                self.estado = "listo"

    def terminar(self, resultado=None) -> None:
        with self._lock:
            self.resultado = resultado
            self.estado = "listo"
            self.porcentaje = 100
            self.actual = ""
            self.fin = time.time()

    def fallar(self, error) -> None:
        with self._lock:
            self.error = str(error)
            self.estado = "error"
            self.fin = time.time()

    # ── Estado ──────────────────────────────────────────────────────────

    def as_dict(self) -> dict:
        with self._lock:
            out = {
                "ok": self.estado != "error",
                "id": self.id,
                "tipo": self.tipo,
                "estado": self.estado,
                "hechos": self.hechos,
                "total": self.total,
                "actual": self.actual,
                "porcentaje": self.porcentaje,
                "mensaje": self.mensaje,
                "error": self.error,
                "duracion": round((self.fin or time.time()) - self.iniciado, 2),
            }
            if self.estado == "listo":
                out["resultado"] = self.resultado
            return out


class Jobs:
    """Los trabajos que se han arrancado."""

    #: Cuantos trabajos se guardan (los terminados se van quitando).
    MAX = 20

    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: dict = {}

    def lanzar(self, tipo: str, funcion, mensaje: str = "") -> Job:
        """Arranca ``funcion`` en un hilo y devuelve el trabajo.

        ``funcion`` recibe el trabajo (para poder ir contando) y devuelve
        el resultado.
        """
        job = Job(tipo, mensaje)
        with self._lock:
            self._jobs[job.id] = job
            self._podar()
        hilo = threading.Thread(target=self._correr, args=(job, funcion),
                                name=f"trabajo-{tipo}", daemon=True)
        hilo.start()
        return job

    def obtener(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id or "")

    # ── Interno ─────────────────────────────────────────────────────────

    @staticmethod
    def _correr(job: Job, funcion) -> None:
        try:
            resultado = funcion(job)
        except Exception as exc:
            detalle = traceback.format_exc(limit=3)
            job.fallar(f"{exc} ({detalle.strip().splitlines()[-1]})")
            return
        job.terminar(resultado)

    def _podar(self) -> None:
        """Quita los trabajos terminados mas antiguos."""
        if len(self._jobs) <= self.MAX:
            return
        terminados = [j for j in self._jobs.values() if j.estado != "trabajando"]
        terminados.sort(key=lambda j: j.fin or j.iniciado)
        while len(self._jobs) > self.MAX and terminados:
            self._jobs.pop(terminados.pop(0).id, None)


#: Los trabajos del proceso.
JOBS = Jobs()

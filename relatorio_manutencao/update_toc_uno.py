"""Atualiza sumário e campos de um DOCX usando LibreOffice UNO headless."""
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import uno
from com.sun.star.beans import PropertyValue


def propriedade(nome, valor):
    item = PropertyValue()
    item.Name = nome
    item.Value = valor
    return item


def porta_livre():
    with socket.socket() as servidor:
        servidor.bind(("127.0.0.1", 0))
        return servidor.getsockname()[1]


def main():
    caminho = Path(sys.argv[1]).resolve()
    soffice = shutil.which("libreoffice") or shutil.which("soffice")
    if not soffice or not caminho.exists():
        return 2

    porta = porta_livre()
    perfil = Path(tempfile.mkdtemp(prefix="engvi_uno_"))
    processo = subprocess.Popen(
        [
            soffice,
            "--headless",
            "--nologo",
            "--nodefault",
            "--norestore",
            f"-env:UserInstallation=file://{perfil.as_posix()}",
            f"--accept=socket,host=127.0.0.1,port={porta};urp;StarOffice.ComponentContext",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    documento = None
    desktop = None
    try:
        contexto_local = uno.getComponentContext()
        resolvedor = contexto_local.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", contexto_local
        )
        contexto = None
        for _ in range(40):
            try:
                contexto = resolvedor.resolve(
                    f"uno:socket,host=127.0.0.1,port={porta};urp;StarOffice.ComponentContext"
                )
                break
            except Exception:
                time.sleep(0.25)
        if contexto is None:
            return 3

        desktop = contexto.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", contexto
        )
        documento = desktop.loadComponentFromURL(
            caminho.as_uri(),
            "_blank",
            0,
            (propriedade("Hidden", True), propriedade("UpdateDocMode", 3)),
        )
        if documento is None:
            return 4

        indices = documento.getDocumentIndexes()
        for indice in range(indices.getCount()):
            indices.getByIndex(indice).update()
        documento.calculateAll()
        documento.store()
        return 0
    finally:
        if documento is not None:
            try:
                documento.close(True)
            except Exception:
                pass
        if desktop is not None:
            try:
                desktop.terminate()
            except Exception:
                pass
        try:
            processo.terminate()
            processo.wait(timeout=5)
        except Exception:
            processo.kill()
        shutil.rmtree(perfil, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
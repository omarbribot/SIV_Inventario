import zipfile
import os
from datetime import datetime

def crear_respaldo():
    # Nombre del archivo con la fecha de hoy
    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nombre_zip = f"Respaldo_Inventario_{fecha}.zip"
    
    # Carpetas y archivos que NO queremos incluir
    ignorar = {'.venv', '__pycache__', '.git', '.vscode', 'respaldar.py'}
    
    print(f"--- Iniciando respaldo: {nombre_zip} ---")
    
    with zipfile.ZipFile(nombre_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for raiz, carpetas, archivos in os.walk('.'):
            # Filtrar carpetas ignoradas
            carpetas[:] = [d for d in carpetas if d not in ignorar]
            
            for archivo in archivos:
                # No incluir el propio archivo zip que se está creando
                if archivo == nombre_zip or archivo in ignorar:
                    continue
                    
                ruta_completa = os.path.join(raiz, archivo)
                # Guardar en el zip manteniendo la estructura de carpetas
                zipf.write(ruta_completa, ruta_completa)
                print(f"Agregado: {ruta_completa}")

    print(f"\n¡Listo! Proyecto comprimido en: {os.path.abspath(nombre_zip)}")

if __name__ == "__main__":
    crear_respaldo()
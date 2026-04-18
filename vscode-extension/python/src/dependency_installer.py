import importlib
import subprocess
import sys
import time
from typing import List, Optional


def install_packages(packages: List[str], max_retries: int = 2) -> bool:
    """
    Installiert Pakete via pip mit Retry-Logik.
    
    Args:
        packages: Liste der zu installierenden Pakete
        max_retries: Maximale Anzahl an Installationsversuchen
        
    Returns:
        bool: True wenn alle Pakete erfolgreich installiert wurden
    """
    for package in packages:
        for attempt in range(max_retries + 1):
            try:
                # Versuche, das Paket zu importieren
                importlib.import_module(package)
                print(f"Paket {package} already installed")
                break
            except ImportError:
                print(f"Paket {package} nicht gefunden, versuche Installation...")
                try:
                    # Führe pip install aus
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                    print(f"Paket {package} erfolgreich installiert")
                    break
                except subprocess.CalledProcessError as e:
                    print(f"Installation von {package} fehlgeschlagen (Versuch {attempt + 1}): {e}")
                    if attempt < max_retries:
                        print(f"Warte 2 Sekunden vor nächstem Versuch...")
                        time.sleep(2)
                    else:
                        print(f"Maximale Anzahl an Versuchen erreicht für Paket {package}")
                        return False
    return True


def safe_import(module_name: str, package_name: Optional[str] = None, max_retries: int = 2):
    """
    Sicheres Importieren mit automatischer Installation.
    
    Args:
        module_name: Name des zu importierenden Moduls
        package_name: Name des Pakets, das installiert werden muss (kann sich von module_name unterscheiden)
        max_retries: Maximale Anzahl an Installationsversuchen
        
    Returns:
        Das importierte Modul oder None bei Fehler
    """
    if package_name is None:
        package_name = module_name
    
    try:
        return importlib.import_module(module_name)
    except ImportError:
        print(f"Modul {module_name} nicht gefunden, versuche Installation von {package_name}...")
        if install_packages([package_name], max_retries):
            return importlib.import_module(module_name)
        else:
            print(f"Konnte {module_name} nicht importieren nach {max_retries} Versuchen")
            return None


# Beispiel für die Verwendung in anderen Modulen
# importlib = safe_import("importlib", "importlib")
# requests = safe_import("requests", "requests")

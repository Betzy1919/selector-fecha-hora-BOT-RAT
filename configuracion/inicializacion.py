import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger('AlertasTempranasBot') 
# Configuración de la conexión a PostgreSQL
# Asumo que config_db está en tu archivo principal
config_db = {
    "dbname": os.getenv("DB_DATABASE"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
     "port": os.getenv("DB_PORT", "5432")

}

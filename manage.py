from app import app, db
from flask_migrate import Migrate

migrate = Migrate(app, db)

# Важно: Flask CLI автоматически подхватит app и db

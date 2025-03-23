import os
import yagmail
import cloudinary
import cloudinary.uploader
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 📌 Zona horaria de Colombia (UTC-5)
COL_TIMEZONE = timezone(timedelta(hours=-5))

# 📌 Configuración de la base de datos (Usa PostgreSQL en Render, SQLite localmente)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///SUDEA-IMG.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

# 📌 Configurar Cloudinary con variables de entorno
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# 📌 Configurar correo (Gmail con App Password)
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")
RECEPTOR = os.getenv("EMAIL_RECEPTOR")

# 📌 MODELO DE BASE DE DATOS
class SUDEA_REGISTROS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    ruta = db.Column(db.String(300), nullable=False)
    anomalía_detectada = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(COL_TIMEZONE))

with app.app_context():
    db.create_all()
    print("✅ Base de datos lista.")

# 📌 Verificar si una extensión de archivo es válida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 📌 Función para enviar correos en caso de anomalías
def enviar_correo(imagen_nombre, imagen_url):
    try:
        yag = yagmail.SMTP(EMAIL, PASSWORD)
        asunto = "Nueva Anomalía Detectada"
        cuerpo = f"""\
        **Se ha detectado una anomalía en la imagen**  
        Nombre: {imagen_nombre}  
        URL: {imagen_url}  
        Timestamp: {datetime.now(COL_TIMEZONE)}
        """
        yag.send(to=RECEPTOR, subject=asunto, contents=cuerpo)
        print("✅ Correo enviado con éxito")
    except Exception as e:
        print(f"⚠️ Error enviando correo: {e}")

# 📌 API para subir imágenes manualmente
@app.route('/subir_imagen', methods=['POST'])
def subir_imagen():
    if 'file' not in request.files:
        return jsonify({'error': 'No se encontró ningún archivo'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Formato de archivo no permitido'}), 400

    filename = secure_filename(file.filename)

    try:
        # Subir la imagen a Cloudinary
        upload_result = cloudinary.uploader.upload(file)
        image_url = upload_result['secure_url']

        # Guardar en la base de datos
        nueva_imagen = SUDEA_REGISTROS(nombre=filename, ruta=image_url, anomalía_detectada=False)

        with app.app_context():
            db.session.add(nueva_imagen)
            db.session.commit()

        return jsonify({'message': '✅ Imagen subida correctamente', 'url': image_url}), 200
    except Exception as e:
        return jsonify({'error': f'Error al subir imagen: {e}'}), 500

# 📌 API para marcar anomalías
@app.route('/marcar_anomalia/<int:imagen_id>', methods=['POST'])
def marcar_anomalia(imagen_id):
    imagen = SUDEA_REGISTROS.query.get(imagen_id)

    if not imagen:
        return jsonify({'error': '⚠️ Imagen no encontrada'}), 404

    try:
        imagen.anomalía_detectada = True
        db.session.commit()

        # Enviar correo con la URL de la imagen
        enviar_correo(imagen.nombre, imagen.ruta)

        return jsonify({'message': '✅ Anomalía marcada y correo enviado'}), 200
    except Exception as e:
        return jsonify({'error': f'Error al marcar anomalía: {e}'}), 500

# 📌 Gunicorn se encargará de ejecutar la app en producción


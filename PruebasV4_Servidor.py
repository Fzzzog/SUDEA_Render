import os
import yagmail
import cloudinary
import cloudinary.uploader
import Comparador_Img as c
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Zona horaria de Colombia (UTC-5)
COL_TIMEZONE = timezone(timedelta(hours=-5))

# Configuración de la base de datos
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///SUDEA-IMG.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

db = SQLAlchemy(app)

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Configurar correo
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")
RECEPTOR = os.getenv("EMAIL_RECEPTOR")

'''
FIN DE LAS CONFIGURACIONES
'''

# ESPECIFICAR MODELO DE BASE DE DATOS
class SUDEA_REGISTROS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    ruta = db.Column(db.String(300), nullable=False)
    anomalía_detectada = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(COL_TIMEZONE))

with app.app_context():
    db.create_all()
    print("✅ Base de datos lista.")

'''
DEFINICIÓN DE FUNCIONES
'''

# Verificar extensión de archivo
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Función para enviar correos
def enviar_correo(imagen_nombre, imagen_url, datos_de_alerta):
    try:
        yag = yagmail.SMTP(EMAIL, PASSWORD)
        asunto = "Nueva Anomalía Detectada"
        cuerpo = f"""\
        **Se ha detectado una anomalía en la imagen**  
        Nombre: {imagen_nombre}  
        URL: {imagen_url}  
        Timestamp: {datetime.now(COL_TIMEZONE)}
        \n**Detalles de Alerta**
        PSNR: {datos_de_alerta["psnr"]}
        SSIM: {datos_de_alerta["ssim"]}
        Porcentaje de cambio: {datos_de_alerta["porcentaje_cambio"]}
        Correlación de Histogramas: {datos_de_alerta["histograma"]}
        """
        yag.send(to=RECEPTOR, subject=asunto, contents=cuerpo)
        print(" Correo enviado con éxito")
    except Exception as e:
        print(f" Error enviando correo: {e}")

# Función para subir imágenes
@app.route('/upload', methods=['POST'])
def subir_imagen():
    # Descarte de archivos no válidos
    if 'file' not in request.files:
        return jsonify({'error': 'No se encontró ningún archivo'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Formato de archivo no permitido'}), 400

    # Preparar el nombre del archivo
    filename = secure_filename(file.filename)

   try:
    # Subir a Cloudinary
    upload_result = cloudinary.uploader.upload(file)
    image_url = upload_result['secure_url']

    #Obtener la última imagen de la base de datos
    ultima_imagen = SUDEA_REGISTROS.query.order_by(SUDEA_REGISTROS.timestamp.desc()).first()
    img1_url = getattr(ultima_imagen, 'ruta', None)  # Evita errores si es None

    #Comprobar si hay una anomalía comparando las imágenes
    anomalia = c.comparar_imagenes(img1_url, image_url) or {"anomalia": False}

    #Guardar la nueva imagen en la base de datos con el valor de anomalía
    nueva_imagen = SUDEA_REGISTROS(nombre=filename, ruta=image_url, anomalia_detectada=anomalia["anomalia"])
    db.session.add(nueva_imagen)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar en la base de datos: {e}")
        return jsonify({"error": "Error al guardar en la base de datos"}), 500

    #Si hay anomalía se envía la alerta
    if anomalia["anomalia"]:  
        enviar_correo(filename, image_url, anomalia)  

    return jsonify({'message': 'Imagen subida correctamente', 'url': image_url, 'ID': nueva_imagen.id, 'anomalía': anomalia["anomalia"]}), 200

except Exception as e:
    print(f"Error general en la carga de imagen: {e}")
    return jsonify({"error": "Error inesperado"}), 500

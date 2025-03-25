import cv2
import numpy as np
import requests
from skimage.metrics import structural_similarity as ssim

def cargar_imagen(url):
    #Cargar la imagen desde la url de cloud
    resp = requests.get(url)  # Baja la imagen
    if resp.status_code != 200:
        print(f"Error al descargar la imagen: {url}")
        return None

    img_array = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)  # Decodifica la imagen
    return img

#Función cálculo de PSNR
def calcular_psnr(img1, img2):
    return cv2.PSNR(img1, img2)

#Función cálculo de SSIM
def calcular_ssim(img1, img2):
    #Convierte a escala de grises
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    
    ssim_value, _ = ssim(gray1, gray2, full=True)
    return ssim_value

#Función comparar histogramas en el canal verde (pq bosque y plantas)
def calcular_histograma_correlation(img1, img2):
    #Extraer el canal verde
    verde1 = img1[:, :, 1]
    verde2 = img2[:, :, 1]

    #Calcula histogramas 
    hist1 = cv2.calcHist([verde1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([verde2], [0], None, [256], [0, 256])

    #Normalizar los histogramas (ajustar el rango de los valores)
    hist1 = hist1 / hist1.sum()
    hist2 = hist2 / hist2.sum()

    #Calcular la correlación (Qué tanto se parecen)
    correlacion = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

    return correlacion

#Función unificada de comparación de imágenes
def comparar_imagenes(url1, url2, threshold=0.1, psnr_threshold=30, ssim_threshold=0.8, hist_threshold=0.8):
    #Descargar las imágenes del url
    img1 = cargar_imagen(url1)
    img2 = cargar_imagen(url2)

    if img1 is None or img2 is None:
        return None  #Si alguna imagen no se pudo cargar, retorna None

    if img1.shape != img2.shape:
        return {"anomalía": True, "psnr": None, "ssim": None, "histograma": None}  #Si son de tamaños diferentes marca anomalía 

    #Convertir a escala de grises
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    #Calcular la diferencia absoluta
    diff = cv2.absdiff(gray1, gray2)
    porcentaje_cambio = np.sum(diff) / np.prod(gray1.shape)
    anomalía_abs = porcentaje_cambio > threshold

    #Calcular PSNR
    psnr_value = calcular_psnr(img1, img2)
    anomalía_psnr = psnr_value < psnr_threshold  # Umbral bajo indica anomalía

    #Calcular SSIM
    ssim_value = calcular_ssim(img1, img2)
    anomalía_ssim = ssim_value < ssim_threshold  # Umbral bajo indica anomalía

    #Comparar histogramas del canal verde
    hist_correlation = calcular_histograma_correlation(img1, img2)
    anomalía_hist = hist_correlation < hist_threshold  # Correlación baja indica anomalía

    #Determinar si hay una anomalía en cualquier métrica
    anomalía_total = anomalía_abs or anomalía_psnr or anomalía_ssim or anomalía_hist

    #Retorna un diccionario con los datos
    return {
        "anomalia": bool(anomalía_total),
        "psnr": float(round(psnr_value,6)),
        "ssim": float(round(ssim_value,6)),
        "porcentaje_cambio": float(round(porcentaje_cambio,6)),
        "histograma": float(round(hist_correlation,6))
    }

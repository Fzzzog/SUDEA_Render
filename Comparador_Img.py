import cv2
import numpy as np
import requests
from skimage.metrics import structural_similarity as ssim

def cargar_imagen(url):
    #Cargar la imagen desde la url de cloud
    resp = requests.get(url)  # Baja la imagen
    if resp.status_code != 200:
        print(f"❌ Error al descargar la imagen: {url}")
        return None

    img_array = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)  # Decodifica la imagen
    return img

def calcular_psnr(img1, img2):
    """ Calcula el PSNR entre dos imágenes """
    return cv2.PSNR(img1, img2)

def calcular_ssim(img1, img2):
    """ Calcula el SSIM entre dos imágenes """
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    ssim_value, _ = ssim(gray1, gray2, full=True)
    return ssim_value

def calcular_histograma_correlation(img1, img2):
    """ Compara los histogramas del canal verde de dos imágenes """
    # Extraemos el canal verde de las imágenes
    verde1 = img1[:, :, 1]
    verde2 = img2[:, :, 1]

    # Calculamos los histogramas para el canal verde
    hist1 = cv2.calcHist([verde1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([verde2], [0], None, [256], [0, 256])

    # Normalizamos los histogramas
    hist1 = hist1 / hist1.sum()
    hist2 = hist2 / hist2.sum()

    # Calculamos la correlación entre los histogramas
    correlacion = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

    return correlacion

def comparar_imagenes(url1, url2, threshold=0.1, psnr_threshold=30, ssim_threshold=0.8, hist_threshold=0.8):
    """ Compara dos imágenes y calcula métricas de comparación """
    img1 = cargar_imagen(url1)
    img2 = cargar_imagen(url2)

    if img1 is None or img2 is None:
        return None  # Si alguna imagen no se pudo cargar, retornar None

    if img1.shape != img2.shape:
        return {"anomalía": True, "psnr": None, "ssim": None, "histograma": None}  # Si son de tamaños diferentes, hay un cambio claro

    # Convertir a escala de grises
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Calcular la diferencia absoluta
    diff = cv2.absdiff(gray1, gray2)
    porcentaje_cambio = np.sum(diff) / np.prod(gray1.shape)
    anomalía_abs = porcentaje_cambio > threshold

    # Calcular PSNR
    psnr_value = calcular_psnr(img1, img2)
    anomalía_psnr = psnr_value < psnr_threshold  # Umbral bajo indica anomalía

    # Calcular SSIM
    ssim_value = calcular_ssim(img1, img2)
    anomalía_ssim = ssim_value < ssim_threshold  # Umbral bajo indica anomalía

    # Comparar histogramas del canal verde
    hist_correlation = calcular_histograma_correlation(img1, img2)
    anomalía_hist = hist_correlation < hist_threshold  # Correlación baja indica anomalía

    # Determinar si hay una anomalía en cualquier métrica
    anomalía_total = anomalía_abs or anomalía_psnr or anomalía_ssim or anomalía_hist

    return {
        "anomalia": bool(anomalía_total),
        "psnr": float(round(psnr_value,6)),
        "ssim": float(round(ssim_value,6)),
        "porcentaje_cambio": float(round(porcentaje_cambio,6)),
        "histograma": float(round(hist_correlation,6))
    }

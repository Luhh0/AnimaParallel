import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random, math
import threading
from threading import Thread

lock = threading.Lock()
ancho, altura = 600, 600
FPS = 60
DURACION = 10 

COLOR_FONDO = np.array([96, 207, 253]) #Fondo a eliminar del objeto
VELOCIDAD = 15  #Grados por frame

def cargar_y_recortar_estrella(tolerancia=130):

    with open("matriz_objeto.txt", "r") as f:
        matriz = np.array(eval(f.read().split('kernel=np.array(')[1].split(', dtype=np.uint8)')[0]))
    
    #Eliminar fondo con tolerancia
    es_fondo = np.linalg.norm(matriz.astype(int) - COLOR_FONDO.astype(int), axis=-1) <= tolerancia
    
   
    matriz[es_fondo] = 0  #Convertir transparente el fondo
    

    y, x = np.where(~es_fondo)
    if y.size == 0:
        return np.zeros((0, 0, 3), np.zeros((0, 0), dtype=bool))
    
    return matriz[y.min():y.max()+1, x.min():x.max()+1], ~es_fondo[y.min():y.max()+1, x.min():x.max()+1]

def expandir_con_padding(matriz, mascara):
    altura, ancho = matriz.shape[:2]
    nuevo_lado = int(np.ceil(np.sqrt(altura**2 + ancho**2)))

    y_ini = (nuevo_lado - altura) // 2
    x_ini = (nuevo_lado - ancho) // 2

    #Agrandar la máscara creando nuevas matrices
    nueva_matriz = np.zeros((nuevo_lado, nuevo_lado, 3), dtype=np.uint8)
    nueva_mascara = np.zeros((nuevo_lado, nuevo_lado), dtype=bool)

    nueva_matriz[y_ini:y_ini+altura, x_ini:x_ini+ancho] = matriz
    nueva_mascara[y_ini:y_ini+altura, x_ini:x_ini+ancho] = mascara

    return nueva_matriz, nueva_mascara

#Clase para la estrella Principal
class EstrellaRotante:
    def __init__(self):
        self.imagen, self.mascara = cargar_y_recortar_estrella()
        self.imagen, self.mascara = expandir_con_padding(self.imagen, self.mascara)
        self.angulo = 0
        self.centro_pantalla = np.array([ancho // 2, altura // 2])
        self.centro_imagen = np.array([self.imagen.shape[1] // 2, self.imagen.shape[0] // 2])
    
    def rotar(self):
        """Rotación manual rápida"""
        alto, ancho_img = self.imagen.shape[:2]
        imagen_rotada = np.zeros_like(self.imagen)
        mascara_rotada = np.zeros_like(self.mascara, dtype=bool)
        
        radianes = math.radians(self.angulo)
        coseno, seno = math.cos(radianes), math.sin(radianes)
        
        for y in range(alto):
            for x in range(ancho_img):
                x_rel = x - self.centro_imagen[0]
                y_rel = y - self.centro_imagen[1]
                
                x_original = int(self.centro_imagen[0] + x_rel * coseno + y_rel * seno)
                y_original = int(self.centro_imagen[1] - x_rel * seno + y_rel * coseno)
                
                if (0 <= x_original < ancho_img and
                    0 <= y_original < alto and
                    self.mascara[y_original, x_original]):
                    
                    imagen_rotada[y, x] = self.imagen[y_original, x_original]
                    mascara_rotada[y, x] = True
        
        return imagen_rotada, mascara_rotada
    
    def actualizar(self):
        self.angulo = (self.angulo + VELOCIDAD) % 360
    
    def dibujar(self, lienzo):
        imagen_rotada, mascara_rotada = self.rotar()
        alto, ancho_img = imagen_rotada.shape[:2]
        
        x_inicio = self.centro_pantalla[0] - ancho_img // 2
        y_inicio = self.centro_pantalla[1] - alto // 2
        
        for y in range(alto):
            for x in range(ancho_img):
                if mascara_rotada[y, x]:
                    px = x_inicio + x
                    py = y_inicio + y
                    if 0 <= px < ancho and 0 <= py < altura:
                        lienzo[py, px] = imagen_rotada[y, x]

def cargar_fondo():
    try:
        with open("matriz_fondo.txt", "r") as file:
            datos = file.read()
        kernel = np.array(eval(datos.split('kernel=np.array(')[1].split(', dtype=np.uint8)')[0]))
        return kernel.astype(np.uint8)
    except:
        fondo = np.zeros((altura, ancho, 3), dtype=np.uint8)
        fondo[:, :] = [5, 5, 30]  # Azul oscuro
        return fondo

#Clase Varias Estrellas
class Estrella:
    def __init__(self, ancho, alto):
        self.ancho = ancho
        self.alto = alto
        self.reiniciar()
    
    def reiniciar(self):
        self.x = random.uniform(0, self.ancho)
        self.y = random.uniform(0, self.alto)
        self.velocidad = random.uniform(2.0, 8.0)
        self.tamano = random.randint(1, 4)
        self.transparencia = random.uniform(0.7, 1.0)
        self.vida = random.randint(80, 200)
        self.vida_maxima = self.vida
        self.tipo = random.choice(["punto", "cruz"])
        self.color = np.array([random.randint(200, 255) for _ in range(3)], dtype=np.uint8)
    
    def actualizar(self):
        self.x -= self.velocidad
        self.vida -= 1
        self.transparencia = max(0, self.vida / self.vida_maxima)
        
        if self.x < -20 or self.vida <= 0:
            self.reiniciar()
            self.x = self.ancho + random.uniform(20, 100)
    
    def aplicar_a_frame(self, frame):
        if self.tipo == "punto":
            self.dibujar_punto(frame)
        elif self.tipo == "cruz":
            self.dibujar_cruz(frame)
    
    def dibujar_punto(self, frame):
        radio = int(self.tamano)
        x, y = int(self.x), int(self.y)
        for dy in range(-radio, radio + 1):
            for dx in range(-radio, radio + 1):
                if dx*dx + dy*dy <= radio*radio:
                    px, py = x + dx, y + dy
                    if 0 <= px < self.ancho and 0 <= py < self.alto:
                        frame[py, px] = self.mezclar_pixeles(frame[py, px], self.color, self.transparencia)
    
    def dibujar_cruz(self, frame):
        largo = self.tamano * 2
        x, y = int(self.x), int(self.y)
        for i in range(-largo, largo + 1):
            for px, py in [(x + i, y), (x, y + i)]:
                if 0 <= px < self.ancho and 0 <= py < self.alto:
                    frame[py, px] = self.mezclar_pixeles(frame[py, px], self.color, self.transparencia)

    def mezclar_pixeles(pixel_fondo, pixel_estrella, transparencia):
        return (pixel_fondo * (1 - transparencia) + pixel_estrella * transparencia).astype(np.uint8)
def main():
    #Cargar fondo y objeto (esto sigue igual)
    fondo = cargar_fondo()
    
    with open("matriz_arcoiris.txt", "r") as archivo:
        datos = archivo.read()
    arcoiris = np.array(eval(datos.split('kernel=np.array(')[1].split(', dtype=np.uint8)')[0]), dtype=np.uint8)

    alto_arcoiris, ancho_arcoiris = arcoiris.shape[:2]
    desfase_x_arcoiris = 185
    desfase_y_arcoiris = 250

    #Creamos los objetos
    estrellas = [Estrella(ancho, altura) for _ in range(150)]
    objeto_rotante = EstrellaRotante()
    
    desplazamiento = 5
    estado_movimiento = [0]

    #Configuración de matplotlib
    figura, ejes = plt.subplots(figsize=(8, 8))
    imagen = ejes.imshow(fondo, interpolation='bilinear')
    ejes.axis('off')
    plt.tight_layout()
            

    def actualizar_estrellas(estrellas, cuadro_actual):
        for estrella in estrellas:
            estrella.actualizar()
            estrella.aplicar_a_frame(cuadro_actual)
    

    def rotar_objeto(objeto, cuadro_actual):
        objeto.angulo = (objeto.angulo + VELOCIDAD) % 360
        objeto.dibujar(cuadro_actual)

    def actualizar(cuadro):
        cuadro_actual = fondo.copy()
        
        # Alterna movimiento cada 1 frame
        estado_movimiento[0] = 1 - estado_movimiento[0]
        
        #Procesamiento del arcoiris
        zonas = [
            {'x': (0, 41), 'y': (0, 90), 'dir_x': 1, 'dir_y': -1},
            {'x': (42, 83), 'y': (0, 93), 'dir_x': 0, 'dir_y': 1},
            {'x': (84, 120), 'y': (0, 93), 'dir_x': -1, 'dir_y': -1}
        ]
        
        for zona in zonas:
            x_ini, x_fin = zona['x']
            y_ini, y_fin = zona['y']
            despl_x = desplazamiento * zona['dir_x'] * estado_movimiento[0]
            despl_y = desplazamiento * zona['dir_y'] * estado_movimiento[0]
            
            for y in range(y_ini, y_fin + 1):
                nuevo_y = y + despl_y
                if 0 <= nuevo_y < alto_arcoiris:
                    for x in range(x_ini, x_fin + 1):
                        nuevo_x = x + despl_x
                        if 0 <= nuevo_x < ancho_arcoiris:
                            if not np.all(arcoiris[y, x] <= 10):
                                px = desfase_x_arcoiris + nuevo_x
                                py = desfase_y_arcoiris + nuevo_y
                                if 0 <= px < ancho and 0 <= py < altura:
                                    cuadro_actual[py, px] = arcoiris[y, x]
        
        #Dibujar zona no movil del arcoiris
        for y in range(alto_arcoiris):
            for x in range(ancho_arcoiris):
                en_zona_movil = False
                for zona in zonas:
                    x_ini, x_fin = zona['x']
                    y_ini, y_fin = zona['y']
                    if x_ini <= x <= x_fin and y_ini <= y <= y_fin:
                        en_zona_movil = True
                        break
                
                if not en_zona_movil and not np.all(arcoiris[y, x] <= 10):
                    px = desfase_x_arcoiris + x
                    py = desfase_y_arcoiris + y
                    if 0 <= px < ancho and 0 <= py < altura:
                        cuadro_actual[py, px] = arcoiris[y, x]

        #Dividimos las estrellas en dos grupos 
        mitad = len(estrellas) // 2
        grupo1 = estrellas[:mitad]
        grupo2 = estrellas[mitad:]
        
        #Creamos threads
        thread1 = Thread(target=actualizar_estrellas, args=(grupo1, cuadro_actual))
        thread2 = Thread(target=actualizar_estrellas, args=(grupo2, cuadro_actual))
        thread3 = Thread(target=rotar_objeto, args=(objeto_rotante, cuadro_actual))
        
        #Iniciamos threads
        thread1.start()
        thread2.start()
        thread3.start()
        
        #Esperamos a que terminen
        thread1.join()
        thread2.join()
        thread3.join()

        imagen.set_array(cuadro_actual)
        return [imagen]
    
    animacion = animation.FuncAnimation(
        figura, actualizar,
        frames=FPS * DURACION,
        interval=1000 / FPS,
        blit=True
    )
    
    plt.show()

if __name__ == "__main__":
    main()

import math
import random
from models import Torneo, Equipo, Partido # Asumiendo que 'models.py' está en el mismo directorio

# ==============================================================================
# 1. CREACIÓN DEL TORNEO
# ==============================================================================

def crear_nuevo_torneo(session, nombre_torneo, num_equipos):
    """
    Crea un nuevo objeto Torneo y lo guarda en la base de datos.
    Retorna el objeto Torneo si la creación es exitosa.
    """
    # 1. Validación de Potencia de 2 (La lógica de Colab se mantiene)
    try:
        if num_equipos < 2 or not math.isclose(math.log2(num_equipos), round(math.log2(num_equipos))):
            return None, "Error: El número de equipos debe ser una potencia de 2 (2, 4, 8, 16, etc.)."
    except ValueError:
        return None, "Error: El número de equipos no es válido."

    # 2. Creación del objeto ORM
    nuevo_torneo = Torneo(
        nombre=nombre_torneo,
        num_equipos=num_equipos,
        formato='Eliminación Directa Simple',
        campeon=None
    )
    
    # 3. Guardar en la base de datos (Persistencia)
    session.add(nuevo_torneo)
    session.commit()
    
    return nuevo_torneo, "Torneo creado con éxito."


# ==============================================================================
# 2. GESTIÓN DE PARTICIPANTES
# ==============================================================================

def agregar_equipo_a_torneo(session, torneo_id, equipo_nombre):
    """
    Agrega un equipo a un torneo existente.
    """
    torneo = session.get(Torneo, torneo_id)
    
    if not torneo:
        return False, "Error: Torneo no encontrado."
    
    # 1. Validar que no exceda el límite
    if len(torneo.equipos) >= torneo.num_equipos:
        return False, f"Error: El torneo ya tiene el límite de {torneo.num_equipos} equipos."

    # 2. Validar que el nombre no esté duplicado
    nombres_existentes = [e.nombre.lower() for e in torneo.equipos]
    if equipo_nombre.strip().lower() in nombres_existentes:
        return False, "Error: Ya existe un equipo con ese nombre en este torneo."

    # 3. Creación y Guardado del objeto Equipo
    nuevo_equipo = Equipo(nombre=equipo_nombre.strip(), torneo=torneo)
    session.add(nuevo_equipo)
    session.commit()
    
    return True, f"Equipo '{equipo_nombre}' agregado con éxito."


# ==============================================================================
# 3. GENERACIÓN DEL BRACKET INICIAL
# ==============================================================================

def generar_bracket_inicial(session, torneo_id):
    """
    Genera y guarda los partidos de la Ronda 1 de forma aleatoria.
    """
    torneo = session.get(Torneo, torneo_id)
    
    if not torneo:
        return False, "Error: Torneo no encontrado."
    if len(torneo.equipos) != torneo.num_equipos:
        return False, f"Error: Faltan equipos. Requiere {torneo.num_equipos}, tiene {len(torneo.equipos)}."
    if session.query(Partido).filter(Partido.torneo_id == torneo_id).count() > 0:
        return False, "Error: El bracket ya ha sido generado para este torneo."


    participantes = [e.nombre for e in torneo.equipos]
    random.shuffle(participantes)
    
    num_partidos_ronda_1 = torneo.num_equipos // 2
    ronda_nombre = 'Ronda 1'
    
    # Pre-cálculo del Mapa de Avance (Lógica compleja de Colab adaptada)
    # Genera los IDs de R2: R2_P1, R2_P2, ...
    ronda_siguiente_matches = [f'R2_P{i+1}' for i in range(num_partidos_ronda_1 // 2)]
    advancement_map = {}
    
    for i in range(num_partidos_ronda_1):
        match_id = f'R1_P{i + 1}'
        # Asigna el ID del partido destino en R2
        siguiente_id = ronda_siguiente_matches[i // 2] 
        advancement_map[match_id] = siguiente_id

    # Creación de los objetos Partido e inserción en DB
    nuevos_partidos = []
    for i in range(num_partidos_ronda_1):
        match_id = f'R1_P{i + 1}'
        
        partido = Partido(
            torneo=torneo,
            match_id=match_id,
            ronda_nombre=ronda_nombre,
            equipo_a=participantes[i * 2],
            equipo_b=participantes[i * 2 + 1],
            siguiente_partido_id=advancement_map[match_id]
        )
        nuevos_partidos.append(partido)

    session.add_all(nuevos_partidos)
    session.commit()
    return True, f"Bracket inicial ({num_partidos_ronda_1} partidos) generado con éxito."

# ==============================================================================
# 4. INGRESO Y VALIDACIÓN DE RESULTADOS
# ==============================================================================

def ingresar_resultado(session, torneo_id, match_id, marcador_a, marcador_b):
    """
    Busca un partido específico y actualiza su marcador y el campo 'ganador'.
    """
    
    # 1. Buscar el partido por ID lógico y torneo ID
    partido = session.query(Partido).filter(
        Partido.torneo_id == torneo_id,
        Partido.match_id == match_id
    ).first()

    if not partido:
        return False, f"Error: Partido con ID {match_id} no encontrado en el torneo."
    
    # 2. Validaciones
    if marcador_a < 0 or marcador_b < 0:
        return False, "Error: Los marcadores no pueden ser números negativos."
    
    if marcador_a == marcador_b:
        return False, "Error: En Eliminación Directa Simple no se permiten empates. Reingresa los marcadores."

    # 3. Determinar el ganador
    if marcador_a > marcador_b:
        ganador = partido.equipo_a
    else:
        ganador = partido.equipo_b
        
    # 4. Actualizar el objeto Partido
    partido.marcador_a = marcador_a
    partido.marcador_b = marcador_b
    partido.ganador = ganador
    
    session.commit()
    
    mensaje = (f"Resultado registrado para {partido.equipo_a} vs {partido.equipo_b}. "
               f"Marcador: {marcador_a}-{marcador_b}. Ganador: {ganador}.")
    
    return True, mensaje

# ==============================================================================
# 5. OBTENER PARTIDOS PENDIENTES (Para la vista web)
# ==============================================================================

def obtener_partidos_pendientes(session, torneo_id):
    """
    Retorna una lista de objetos Partido que aún no tienen un ganador registrado.
    """
    partidos_pendientes = session.query(Partido).filter(
        Partido.torneo_id == torneo_id,
        Partido.ganador.is_(None)
    ).order_by(Partido.ronda_nombre).all()
    
    return partidos_pendientes

# ==============================================================================
# 6. AVANCE DE RONDA Y DETERMINACIÓN DEL CAMPEÓN
# ==============================================================================

def avanzar_ronda(session, torneo_id):
    """
    Verifica si la última ronda está completa y genera los partidos de la siguiente.
    Si solo queda un partido y está completo, declara al campeón.
    """
    torneo = session.get(Torneo, torneo_id)
    if not torneo:
        return False, "Error: Torneo no encontrado."
    
    # 1. Obtener la última ronda generada
    # Usamos subconsultas para encontrar el nombre de la ronda con el número más alto (ej. 'Ronda 1', 'Ronda 2')
    ultima_ronda_nombre = session.query(Partido.ronda_nombre).filter(
        Partido.torneo_id == torneo_id
    ).order_by(Partido.ronda_nombre.desc()).first()
    
    if not ultima_ronda_nombre:
        return False, "Error: No hay partidos generados. Ejecuta primero la generación del bracket."
    
    ronda_actual_nombre = ultima_ronda_nombre[0]
    ronda_actual_num = int(ronda_actual_nombre.split(' ')[-1])
    
    partidos_ronda_actual = session.query(Partido).filter(
        Partido.torneo_id == torneo_id,
        Partido.ronda_nombre == ronda_actual_nombre
    ).all()
    
    # 2. Verificar si la ronda está completa y recolectar ganadores
    ganadores_ronda = []
    for partido in partidos_ronda_actual:
        if partido.ganador is None:
            return False, f"Advertencia: La ronda '{ronda_actual_nombre}' no está completa. El partido {partido.match_id} no tiene resultado."
        ganadores_ronda.append({
            'ganador': partido.ganador,
            'siguiente_partido_id': partido.siguiente_partido_id # ID del partido en la siguiente ronda (ej. R2_P1)
        })

    # 3. Determinar si el torneo ha finalizado (solo 1 partido en la ronda)
    if len(partidos_ronda_actual) == 1:
        torneo.campeon = partidos_ronda_actual[0].ganador
        session.commit()
        return True, f"¡TORNEO FINALIZADO! El campeón es: {torneo.campeon}"

    # 4. Generar la Estructura de la Siguiente Ronda (Ronda N+1)
    
    ronda_siguiente_num = ronda_actual_num + 1
    ronda_siguiente_nombre = f'Ronda {ronda_siguiente_num}'
    num_partidos_siguiente = len(partidos_ronda_actual) // 2
    
    # 5. Calcular los ID de avance para la ronda N+1 (Destino: Ronda N+2)
    # Si la siguiente ronda tiene más de 1 partido, necesitamos calcular el avance
    if num_partidos_siguiente > 1:
        ronda_destino_num = ronda_siguiente_num + 1
        num_partidos_destino = num_partidos_siguiente // 2
        
        # Generamos los IDs de destino (ej. R3_P1, R3_P2, ...)
        ronda_destino_matches = [f'R{ronda_destino_num}_P{i+1}' for i in range(num_partidos_destino)]
    else:
        # Si la siguiente ronda es la final, el avance es None (no hay más rondas)
        ronda_destino_matches = [None] 
        
    
    # 6. Agrupar ganadores para formar los nuevos emparejamientos
    partidos_en_construccion = {}
    
    for i, item in enumerate(ganadores_ronda):
        target_id = item['siguiente_partido_id'] # target_id es un ID de Ronda N+1 (ej. R2_P1)
        
        if target_id not in partidos_en_construccion:
            # Si es el primer equipo, usa equipo_a y calcula su avance a Ronda N+2
            
            # La posición del partido en la siguiente ronda es el índice i dividido por 2
            advancement_index = i // 2 
            siguiente_partido_destino = ronda_destino_matches[advancement_index]
            
            partidos_en_construccion[target_id] = {
                'equipo_a': item['ganador'],
                'equipo_b': None,
                'siguiente_partido_id': siguiente_partido_destino
            }
        else:
            # Si es el segundo equipo, llena equipo_b
            partidos_en_construccion[target_id]['equipo_b'] = item['ganador']


    # 7. Crear los nuevos objetos Partido (Ronda N+1)
    nuevos_partidos = []
    for match_id, data in partidos_en_construccion.items():
        if data['equipo_b'] is None:
             session.rollback()
             return False, "Error lógico: Faltan equipos para la siguiente ronda. Revisar."
             
        nuevo_partido = Partido(
            torneo=torneo,
            match_id=match_id,
            ronda_nombre=ronda_siguiente_nombre,
            equipo_a=data['equipo_a'],
            equipo_b=data['equipo_b'],
            siguiente_partido_id=data['siguiente_partido_id']
        )
        nuevos_partidos.append(nuevo_partido)

    session.add_all(nuevos_partidos)
    session.commit()
    return True, f"Ronda {ronda_siguiente_num} generada con {num_partidos_siguiente} partidos."
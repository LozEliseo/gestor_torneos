import os
from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, Torneo, Equipo, Partido # Importamos los modelos de la DB
import tournament_logic as logic # Importamos nuestra lógica de negocio

# --- CONFIGURACIÓN DE LA APLICACIÓN Y BASE DE DATOS ---

# Directorio base para la base de datos (gestor.db)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'gestor.db')
# Creamos la carpeta 'instance' si no existe
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

# 1. Creación del motor de la base de datos SQLite
ENGINE = create_engine(f"sqlite:///{DB_PATH}")

# 2. Inicialización de la base de datos
# Crea las tablas si no existen, usando la definición de Base en models.py
Base.metadata.create_all(ENGINE)

# 3. Configuración de la sesión de SQLAlchemy
# scoped_session es esencial para una aplicación web (maneja hilos de ejecución)
Session = scoped_session(sessionmaker(bind=ENGINE))

def create_app():
    """Función factoría para crear y configurar la aplicación Flask."""
    app = Flask(__name__, instance_relative_config=True)
    # Una clave secreta es necesaria para manejar sesiones y mensajes flash
    app.config['SECRET_KEY'] = 'una_clave_secreta_muy_segura' 

    # Middleware para manejar la sesión después de cada solicitud
    @app.teardown_appcontext
    def remove_session(exception=None):
        """Cierra la sesión de SQLAlchemy al final de la solicitud."""
        Session.remove()

    return app

app = create_app()

# --- RUTAS DE LA APLICACIÓN ---

@app.route('/')
def index():
    """Ruta principal: Muestra la lista de torneos."""
    session = Session()
    torneos = session.query(Torneo).all()
    return render_template('index.html', torneos=torneos)

@app.route('/crear', methods=['GET', 'POST'])
def crear_torneo():
    """Muestra el formulario y procesa la creación de un nuevo torneo."""
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        num_equipos = request.form.get('num_equipos')
        
        # Validaciones básicas del formulario
        if not nombre or not num_equipos:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('crear_torneo'))
            
        try:
            num_equipos = int(num_equipos)
        except ValueError:
            flash('El número de equipos debe ser un valor numérico.', 'error')
            return redirect(url_for('crear_torneo'))
            
        session = Session()
        # Llamada a la lógica de negocio (tournament_logic.py)
        nuevo_torneo, mensaje = logic.crear_nuevo_torneo(session, nombre, num_equipos)
        
        if nuevo_torneo:
            flash(f'Torneo "{nombre}" creado con éxito. {mensaje}', 'success')
            return redirect(url_for('dashboard', torneo_id=nuevo_torneo.id))
        else:
            flash(f'Error al crear el torneo: {mensaje}', 'error')
            return redirect(url_for('crear_torneo'))
            
    return render_template('crear_torneo.html')

@app.route('/torneo/<int:torneo_id>')
def dashboard(torneo_id):
    """Muestra el panel de control, equipos, y el bracket de un torneo."""
    session = Session()
    torneo = session.get(Torneo, torneo_id)
    
    if not torneo:
        flash('Torneo no encontrado.', 'error')
        return redirect(url_for('index'))
        
    # Obtener el estado del bracket y los partidos pendientes
    partidos_pendientes = logic.obtener_partidos_pendientes(session, torneo_id)
    
    # Aquí es donde, en el futuro, se llamaría a una función que formatee 
    # todos los partidos del torneo para mostrarlos como un bracket visual.
    bracket_data = session.query(Partido).filter(Partido.torneo_id == torneo_id).all()
    
    return render_template('dashboard.html', 
                           torneo=torneo, 
                           equipos=torneo.equipos,
                           partidos_pendientes=partidos_pendientes,
                           bracket_data=bracket_data)

# Si ejecutas el archivo directamente, inicia el servidor
if __name__ == '__main__':
    # Usamos host='0.0.0.0' para que sea accesible desde otros dispositivos en tu red
    # (útil si estás usando un entorno como WSL o una VM)
    app.run(debug=True, host='0.0.0.0')

# --- RUTAS DE ACCIÓN DEL TORNEO ---

@app.route('/torneo/<int:torneo_id>/agregar_equipo', methods=['POST'])
def agregar_equipo(torneo_id):
    """Procesa la adición de un nuevo equipo al torneo."""
    session = Session()
    equipo_nombre = request.form.get('equipo_nombre')
    
    if not equipo_nombre:
        flash('El nombre del equipo es obligatorio.', 'error')
        return redirect(url_for('dashboard', torneo_id=torneo_id))
    
    exito, mensaje = logic.agregar_equipo_a_torneo(session, torneo_id, equipo_nombre)
    
    if exito:
        flash(mensaje, 'success')
    else:
        flash(mensaje, 'error')
        
    return redirect(url_for('dashboard', torneo_id=torneo_id))

@app.route('/torneo/<int:torneo_id>/generar_bracket', methods=['POST'])
def generar_bracket(torneo_id):
    """Genera la Ronda 1 del bracket si el torneo tiene el número correcto de equipos."""
    session = Session()
    
    exito, mensaje = logic.generar_bracket_inicial(session, torneo_id)
    
    if exito:
        flash(mensaje, 'success')
    else:
        flash(mensaje, 'error')
        
    return redirect(url_for('dashboard', torneo_id=torneo_id))


@app.route('/torneo/<int:torneo_id>/ingresar_resultado', methods=['POST'])
def ingresar_resultado_web(torneo_id):
    """Procesa el ingreso de resultados para un partido específico."""
    session = Session()
    match_id = request.form.get('match_id')
    
    try:
        marcador_a = int(request.form.get('marcador_a'))
        marcador_b = int(request.form.get('marcador_b'))
    except (TypeError, ValueError):
        flash('Los marcadores deben ser números enteros.', 'error')
        return redirect(url_for('dashboard', torneo_id=torneo_id))
        
    exito, mensaje = logic.ingresar_resultado(session, torneo_id, match_id, marcador_a, marcador_b)
    
    if exito:
        flash(mensaje, 'success')
    else:
        flash(mensaje, 'error')
        
    return redirect(url_for('dashboard', torneo_id=torneo_id))

@app.route('/torneo/<int:torneo_id>/avanzar_ronda', methods=['POST'])
def avanzar_ronda_web(torneo_id):
    """Intenta avanzar a la siguiente ronda o declara al campeón."""
    session = Session()
    
    exito, mensaje = logic.avanzar_ronda(session, torneo_id)
    
    # Manejamos el caso de finalización del torneo, donde el campeón se establece
    torneo_actualizado = session.get(Torneo, torneo_id)
    if torneo_actualizado.campeon:
        flash(mensaje, 'success')
    elif exito:
        flash(mensaje, 'success')
    else:
        flash(mensaje, 'warning') # Usamos warning si la ronda no está completa

    return redirect(url_for('dashboard', torneo_id=torneo_id))

# Añade esta línea al final de tu archivo app.py si aún no la tienes
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
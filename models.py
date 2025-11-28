from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Define la base declarativa para SQLAlchemy
Base = declarative_base()

class Torneo(Base):
    __tablename__ = 'torneos'
    
    # Columnas principales
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    num_equipos = Column(Integer, nullable=False)
    formato = Column(String(50), default='Eliminación Directa Simple')
    campeon = Column(String(100), nullable=True) # Nombre del campeón
    
    # Relación 1:N con Equipos (Un torneo tiene muchos equipos)
    equipos = relationship("Equipo", back_populates="torneo", cascade="all, delete-orphan")
    # Relación 1:N con Partidos (Un torneo tiene muchos partidos)
    partidos = relationship("Partido", back_populates="torneo", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Torneo(id={self.id}, nombre='{self.nombre}', equipos={self.num_equipos})>"

class Equipo(Base):
    __tablename__ = 'equipos'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False, unique=True)
    
    # Clave Foránea: Relaciona cada equipo con su torneo padre
    torneo_id = Column(Integer, ForeignKey('torneos.id'), nullable=False)
    torneo = relationship("Torneo", back_populates="equipos")

    def __repr__(self):
        return f"<Equipo(id={self.id}, nombre='{self.nombre}')>"

class Partido(Base):
    __tablename__ = 'partidos'
    
    id = Column(Integer, primary_key=True)
    
    # Clave Foránea: Relaciona cada partido con su torneo padre
    torneo_id = Column(Integer, ForeignKey('torneos.id'), nullable=False)
    torneo = relationship("Torneo", back_populates="partidos")
    
    # Detalles del partido
    match_id = Column(String(50), nullable=False) # El ID lógico (ej. R1_P1, R2_P1)
    ronda_nombre = Column(String(50), nullable=False) # Nombre de la ronda (ej. Ronda 1)
    
    equipo_a = Column(String(100), nullable=False)
    equipo_b = Column(String(100), nullable=False)
    
    # Resultados
    marcador_a = Column(Integer, nullable=True)
    marcador_b = Column(Integer, nullable=True)
    ganador = Column(String(100), nullable=True)
    
    # Lógica de avance
    siguiente_partido_id = Column(String(50), nullable=True) # ID del partido al que avanza el ganador
    
    def __repr__(self):
        return f"<Partido(id={self.id}, match_id='{self.match_id}', ronda='{self.ronda_nombre}', avance='{self.siguiente_partido_id}')>"
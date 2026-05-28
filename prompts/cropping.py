"""
Prompts for the Cropping phase (bounding box detection for main sections).
"""

CROPPING_PROMPT = (
    "Analiza esta imagen de una hoja de anotación FIBA ya recortada, enderezada y sin fondo externo.\n"
    "Necesito dividirla en exactamente 5 secciones para OCR posterior.\n\n"
    "Devuelve bounding boxes normalizados de 0 a 1000 usando campos nombrados x_min, y_min, x_max, y_max.\n"
    "x_min/x_max son coordenadas horizontales desde la izquierda; y_min/y_max son coordenadas verticales desde arriba.\n\n"
    "Incluye confidence como número de 0 a 1 si puedes estimarlo; si no, usa null.\n\n"
    "Secciones requeridas, con estos nombres exactos:\n"
    "1. header: franja superior con datos generales del partido, torneo, fecha, cancha, árbitros y equipos.\n"
    "2. team_a: bloque del equipo A con jugadores, faltas y puntos individuales; está debajo del header y a la izquierda.\n"
    "3. team_b: bloque del equipo B con jugadores, faltas y puntos individuales; está debajo de team_a y a la izquierda.\n"
    "4. progressive_score: bloque grande de anotación progresiva; normalmente está a la derecha de team_a/team_b.\n"
    "5. footer: franja inferior con marcador final, ganador, periodos, firmas u observaciones.\n\n"
    "Reglas de precisión:\n"
    "- Ajusta cada caja a los bordes visibles de su sección, incluyendo líneas y texto de esa sección.\n"
    "- Evita invadir secciones vecinas; es mejor dejar un margen mínimo interno que mezclar datos.\n"
    "- El header y footer suelen cubrir casi todo el ancho útil de la hoja.\n"
    "- team_a debe quedar arriba de team_b; progressive_score debe cubrir la zona de anotación progresiva completa.\n"
    "- Responde solamente JSON válido que cumpla el schema."
)

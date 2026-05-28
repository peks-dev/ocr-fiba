"""
Prompts detallados para extracción de secciones de hojas FIBA.
Migrados desde extract_sections.py.
"""

# =============================================================================
# HEADER
# =============================================================================
HEADER_PROMPT = """Eres un experto en documentos oficiales de baloncesto de México. Presta atención estricta a la ortografía en español, incluyendo tildes, diéresis y la letra 'ñ'. Nunca reemplaces 'ñ' por 'n'.

Extrae datos visibles del encabezado de una hoja FIBA de baloncesto.
Responde solo JSON. No inventes datos: usa null si no se ve claro.

Lee por campos visuales:
- league: nombre de la liga u organización en el encabezado.
- tournament: torneo/temporada visible. Conserva años completos como 2025, 2025-26 o 2026 según se vean.
- date: valor del campo Fecha. Conserva el formato visible, normalmente dd/mm/aaaa.
- time: valor del campo Hora. Conserva el formato visible, normalmente hh:mm.
- gender: rama/género visible.
- first_judge y second_judge:
  - Lee la línea de jueces/árbitros correspondiente.
  - Si hay una inicial antes del nombre, transcribe esa letra y el nombre.
  - Si solo hay nombre visible, transcribe solo el nombre.
  - Escribe sin puntos: "M. Efrain" -> "m efrain"; "C. Freddy" -> "c freddy".
  - Usa minúsculas.

Para dígitos pequeños en fecha, hora y torneo, lee el campo directamente en la zona donde está escrito; conserva lo visible sin inferir por otras hojas.
"""

# =============================================================================
# TEAM (team_a y team_b) - Usa Markdown
# =============================================================================
TEAM_PROMPT = """Eres un experto en documentos oficiales de baloncesto de México. Presta atención estricta a la ortografía en español, incluyendo tildes, diéresis y la letra 'ñ'. Si lees un nombre que podría llevar 'ñ' (ej: "peña", "muñoz", "ocaña"), escríbelo con 'ñ', no con 'n'. Nunca reemplaces 'ñ' por 'n'.

Extrae únicamente los datos visibles de esta sección de equipo de una hoja FIBA.

Instrucciones generales:
- Analiza la imagen por apartados visuales sin mezclar datos entre ellos.
- Prioriza el análisis visual (lo que realmente está escrito o marcado en las celdas) por encima de la lectura lineal del OCR.
- Para texto/números ilegibles usa null.
- Para casillas vacías usa el valor vacío indicado por el esquema.
- Extrae solo datos visibles de esta sección.

## Apartado 1: Nombre del equipo
- Lee solo la franja superior destacada.
- Transcribe literalmente el nombre visible del equipo.
- Si la franja está vacía o ilegible, usa null.
- No extraigas faltas de equipo por periodo; ese apartado se procesa por separado con otro recorte.

## Apartado 2: Tabla de jugadores
- Procesa la tabla fila por fila de arriba hacia abajo.
- Cada jugador se extrae como una unidad visual: dorsal, nombre, puntos, entrada e inicial, y faltas pertenecen a la misma línea horizontal.
- Incluye una fila cuando tenga al menos uno de estos datos visibles: dorsal, nombre, puntos, marca de entrada/inicial o faltas.
- Usa las líneas horizontales impresas de la tabla para delimitar cada fila. Las marcas escritas cerca de una línea divisoria pertenecen a la celda donde cae la mayor parte del trazo.
- En esta hoja el anotador puede escribir números, X y faltas en la parte baja de la fila, tocando la línea horizontal inferior. Cuando una marca está sobre la línea inferior de una fila o justo encima de ella, asígnala a la fila superior de esa línea.
- Solo asigna una marca a la fila inferior cuando el trazo esté claramente dentro del espacio entre sus dos líneas horizontales.
- Algunas casillas vacías están canceladas con una raya horizontal larga. Clasifica esa raya como casilla vacía/cancelada, no como número, X, inicial ni falta.
- Si una fila tiene nombre visible y una raya horizontal larga en `No.`, `E` o faltas, conserva la fila y usa valores vacíos para esas casillas.
- Dorsal (`number`):
  - Lee la celda angosta de número/dorsal de esa fila.
  - Conserva ceros iniciales, por ejemplo 01.
  - Usa null si la celda de dorsal está vacía.
  - Una raya horizontal larga en la celda de dorsal significa que no hay dorsal registrado; usa null.
- Nombre (`name`):
  - Lee la celda amplia de nombre de esa misma fila.
  - Transcribe literalmente lo visible en español, conservando ñ, tildes y abreviaturas.
  - Si el nombre está parcialmente cortado, transcribe la parte visible.
  - Si la celda de nombre está vacía, usa null.
- Columnas de puntos (puntos_1, puntos_2, puntos_3):
  - Lee las tres celdas de puntos de esa misma fila, de izquierda a derecha.
  - `one_point`: columna de tiros de 1 punto.
  - `two_point`: columna de canastas de 2 puntos.
  - `tree_point`: columna de triples / 3 puntos.
  - Una celda vacía se registra como 0.
  - Una celda con número visible se registra con ese número exacto.
  - Mantén estos valores vinculados a la misma línea horizontal del jugador.
- Columna E (Entrada e Inicial):
  - En JSON, llena `entry_mark` con un solo estado visual para la celda de entrada.
  - `empty`: celda sin marca visible.
  - `entered`: X simple o tacha visible dentro de la celda.
  - `starter`: X dentro de un círculo, X rodeada por un trazo cerrado, o marca claramente circulada.
  - `illegible`: hay una marca visible pero su forma no permite clasificarla.
  - Una raya horizontal larga sin X se clasifica como `empty`.
  - El backend deriva `entered` y `started` desde `entry_mark`.
  - En Markdown, usa la columna entrada para X simple y la columna inicial para X circulada.
- Faltas personales:
  - Procesa las 5 casillas de faltas de cada jugador de izquierda a derecha.
  - En JSON, llena `foul_cells` con exactamente 5 objetos, uno por casilla.
  - Para cada casilla, separa el tipo base (`kind`) del dígito pequeño (`free_throws`).
  - `kind` puede ser: empty, illegible, P, T, U, D, C, B, AD.
  - `free_throws` puede ser: 1, 2, 3 o null.
  - Una casilla vacía usa `kind: "empty"` y `free_throws: null`.
  - Una casilla con una raya horizontal larga de cancelación también usa `kind: "empty"` y `free_throws: null`.
  - Una marca presente pero no legible usa `kind: "illegible"` y `free_throws: null`.
  - Una casilla con solo código base visible usa `kind` con el código base y `free_throws: null`.
  - Una casilla con código base y dígito pequeño visible en la misma casilla usa `kind` con el código base y `free_throws` con 1, 2 o 3.
  - Ejemplo: P2 se representa como `{ "kind": "P", "free_throws": 2 }`; AD1 como `{ "kind": "AD", "free_throws": 1 }`.
  - Deriva `fouls` desde `foul_cells`: P + 2 = P2; AD + 1 = AD1; omite empty e illegible.
  - En Markdown, escribe en la columna faltas solo los códigos visibles, separados por comas y en orden visual.

## Apartado 3: Entrenador/Cap
- Extrae únicamente el texto escrito en la fila inferior correspondiente al nombre del Entrenador/Cap. Ignora las firmas.
"""

# =============================================================================
# TEAM FOULS
# =============================================================================
TEAM_FOULS_PROMPT = """Analiza la sección de Faltas de Equipo. Para cada período (1 al 4), evalúa las 4 casillas de izquierda a derecha.

    Clasifica como 'X' si tiene una cruz o 'X' clara (incluso si está tachada por una línea horizontal larga).

    Clasifica como 'linea_clausura' si tiene el símbolo '=' o un trazo horizontal corto.

    Clasifica como 'vacia' si no hay marcas.
    El total de faltas es la suma exclusiva de las casillas con 'X'"""

# =============================================================================
# PROGRESSIVE SCORE
# =============================================================================
PROGRESSIVE_PROMPT = """
Extrae la anotación progresiva visible de esta sección FIBA.

Devuelve una lista de eventos en orden cronológico por equipo.

Cada evento debe tener:
- player_number: número del jugador que anotó.
- running_score: puntaje acumulado alcanzado por ese equipo después de esa anotación.

## Tu tarea es DETECTAR las marcas, NO clasificarlas:
- En esta tabla hay números pre-impresos (1, 2, 3, 4, 5... hasta ~150) en la columna de running_score.
- El anotador MARCA cada número cuando el equipo alcanza ese puntaje.
- Tu trabajo es: detectar qué números están marcados y leer el dorsal del jugador responsable.


## Cómo leer la tabla:
- Cada marca en la tabla representa que un equipo alcanzó un nuevo puntaje acumulado.
- running_score es el número IMPRESO de la casilla marcada. LEE CON CUIDADO cada número.
- El número del jugador aparece escrito junto a la marca.
- IGNORA las líneas diagonales (↘) en celdas vacías — son marcas de celdas no usadas, no datos de anotación.
- Cualquier marca visible (punto, diagonal, círculo, tachón) indica que ese running_score fue alcanzado.

## Regla crítica de dorsales:
- SOLO reporta un player_number si el número es claramente legible en la imagen.
- Si el dorsal es ilegible, borroso o parcial, usa player_number: null en vez de adivinar.
- Es preferible null a un número incorrecto.

## Reglas de salida:
- No mezcles eventos de A y B.
- Si el running_score está marcado pero el dorsal no es legible, conserva el evento con player_number: null.
- Enfócate en leer correctamente los running_scores — son el dato más importante.
"""

# =============================================================================
# FOOTER
# =============================================================================
FOOTER_PROMPT = """Extrae los datos manuscritos del footer de esta acta de baloncesto.
Responde ÚNICAMENTE con un JSON válido según el esquema. Usa null para campos vacíos o cancelados con rayas horizontales.

### REGLAS DE EXTRACCIÓN Y UBICACIÓN:

1. Puntos por periodo (Bloque central "Marcadores"):
- Lectura VERTICAL: Avanza fila por fila hacia abajo (Período 1 al 4, y extra).
- Extrae el número posado sobre la línea para "A" (team_a) y "B" (team_b).
- Correcciones: Si hay tachones, NO uses null. Extrae el número final legible.

2. Marcador Final (Bloque derecho superior):
- Extrae el total para "Equipo A" y "Equipo B".

3. Equipo Ganador (Bloque derecho inferior):
- Extrae el nombre del equipo.
"""

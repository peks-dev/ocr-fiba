export type RefereePlugin = {
  id: string;
  label: string;
  description: string;
  category: "Extracción" | "Árbitro" | "Regla FIBA";
};

export const REFEREE_PLUGINS: RefereePlugin[] = [
  {
    id: "core_quarter_sums",
    label: "Suma de cuartos",
    description: "Verifica que los cuartos cuadren con el marcador final.",
    category: "Extracción",
  },
  {
    id: "core_duplicate_numbers",
    label: "Dorsales duplicados",
    description: "Detecta dorsales repetidos dentro del mismo equipo.",
    category: "Extracción",
  },
  {
    id: "core_ghost_players",
    label: "Jugadores fantasma",
    description: "Marca anotaciones de dorsales que no aparecen en roster.",
    category: "Extracción",
  },
  {
    id: "core_progressive_vs_final",
    label: "Progresivo vs final",
    description: "Compara el último marcador progresivo contra el final.",
    category: "Extracción",
  },
  {
    id: "core_player_vs_progressive",
    label: "Puntos vs progresivo",
    description: "Cruza los puntos y desglose de tiros de cada jugador contra el tanteo progresivo.",
    category: "Extracción",
  },
  {
    id: "core_progressive_sequence",
    label: "Secuencia progresiva",
    description: "Revisa saltos del tanteo progresivo, dorsales faltantes y suma por cuarto.",
    category: "Extracción",
  },
  {
    id: "core_entry_and_fouls_consistency",
    label: "Entradas y faltas",
    description: "Valida marcas de entrada/titularidad y coherencia entre faltas personales y de equipo.",
    category: "Extracción",
  },
  {
    id: "core_illegible_marks",
    label: "Marcas ilegibles",
    description: "Reporta casillas marcadas como ilegibles durante la extracción.",
    category: "Extracción",
  },
  {
    id: "core_preprocess_fallback",
    label: "Recorte de hoja",
    description: "Avisa si el recorte automático usó la imagen original como respaldo.",
    category: "Extracción",
  },
  {
    id: "referee_player_points_sum",
    label: "Puntos por jugador",
    description: "Compara suma individual de jugadores contra marcador.",
    category: "Árbitro",
  },
  {
    id: "referee_winner_consistency",
    label: "Ganador correcto",
    description: "Verifica que el ganador declarado tenga mayor marcador.",
    category: "Árbitro",
  },
  {
    id: "fiba_player_fouls",
    label: "5 faltas personales",
    description: "Detecta jugadores con más de 5 faltas personales.",
    category: "Regla FIBA",
  },
  {
    id: "fiba_team_fouls",
    label: "Faltas de equipo",
    description: "Revisa faltas de equipo por cuarto.",
    category: "Regla FIBA",
  },
];

export const DEFAULT_REFEREE_PLUGIN_IDS = REFEREE_PLUGINS.map((plugin) => plugin.id);

export function pluginLabel(id: string): string {
  return REFEREE_PLUGINS.find((plugin) => plugin.id === id)?.label || id;
}

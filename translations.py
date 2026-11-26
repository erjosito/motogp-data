"""
MotoGP Dashboard — Translation strings

Usage:
    from translations import get_translator
    t = get_translator("es")
    t("home")  # "Inicio"
"""

TRANSLATIONS = {
    # --- Navigation / Sidebar ---
    "lang_label": {"en": "Language", "es": "Idioma", "it": "Lingua"},
    "viz_home": {"en": "🏠 Home", "es": "🏠 Inicio", "it": "🏠 Home"},
    "viz_rhythm": {"en": "🎯 Pilot Rhythm", "es": "🎯 Ritmo de piloto", "it": "🎯 Ritmo Pilota"},
    "viz_laptimes": {"en": "🏎 Lap Times", "es": "🏎 Tiempos por vuelta", "it": "🏎 Tempi sul Giro"},
    "viz_position": {"en": "📍 Position Battle", "es": "📍 Batalla de posiciones", "it": "📍 Battaglia Posizioni"},
    "viz_distribution": {"en": "📊 Lap Distribution", "es": "📊 Distribución de vueltas", "it": "📊 Distribuzione Giri"},
    "viz_sectors": {"en": "⏱ Sector Heatmap", "es": "⏱ Mapa de sectores", "it": "⏱ Mappa Settori"},
    "viz_tyredeg": {"en": "🛞 Tyre Degradation", "es": "🛞 Degradación de neumáticos", "it": "🛞 Degrado Gomme"},
    "viz_tyrewhisp": {"en": "🧙 Tyre Whisperers", "es": "🧙 Susurradores de neumáticos", "it": "🧙 Sussurratori di Gomme"},
    "viz_speed": {"en": "⚡ Speed Trap", "es": "⚡ Trampa de velocidad", "it": "⚡ Speed Trap"},
    "viz_classification": {"en": "🏆 Classification", "es": "🏆 Clasificación", "it": "🏆 Classifica"},
    "viz_championship": {"en": "🌍 Championship", "es": "🌍 Campeonato", "it": "🌍 Campionato"},
    "viz_teams": {"en": "🏢 Teams & Constructors", "es": "🏢 Equipos y constructores", "it": "🏢 Team e Costruttori"},
    "viz_reliability": {"en": "🔧 Reliability", "es": "🔧 Fiabilidad", "it": "🔧 Affidabilità"},
    "viz_grid": {"en": "🏁 Grid Advantage", "es": "🏁 Ventaja de parrilla", "it": "🏁 Vantaggio Griglia"},
    "viz_circuits": {"en": "🏟 Circuits", "es": "🏟 Circuitos", "it": "🏟 Circuiti"},
    "viz_rankings": {"en": "🏅 Pilot Rankings", "es": "🏅 Ranking de pilotos", "it": "🏅 Classifica Piloti"},
    "viz_profile": {"en": "👤 Pilot Profile", "es": "👤 Perfil del piloto", "it": "👤 Profilo Pilota"},
    "viz_crossyear": {"en": "📈 Cross-Year", "es": "📈 Multi-Temporada", "it": "📈 Multi-Stagione"},

    # --- Sidebar filters ---
    "season": {"en": "Season", "es": "Temporada", "it": "Stagione"},
    "grand_prix": {"en": "Grand Prix", "es": "Gran Premio", "it": "Gran Premio"},
    "session": {"en": "Session", "es": "Sesión", "it": "Sessione"},
    "all_gp": {"en": "All Grand Prix", "es": "Todos los Grandes Premios", "it": "Tutti i Gran Premi"},
    "riders": {"en": "Riders", "es": "Pilotos", "it": "Piloti"},
    "rider": {"en": "Rider", "es": "Piloto", "it": "Pilota"},

    # --- Common labels ---
    "position": {"en": "Position", "es": "Posición", "it": "Posizione"},
    "points": {"en": "Points", "es": "Puntos", "it": "Punti"},
    "wins": {"en": "Wins", "es": "Victorias", "it": "Vittorie"},
    "podiums": {"en": "Podiums", "es": "Podios", "it": "Podi"},
    "poles": {"en": "Poles", "es": "Poles", "it": "Pole"},
    "laps": {"en": "Laps", "es": "Vueltas", "it": "Giri"},
    "lap": {"en": "Lap", "es": "Vuelta", "it": "Giro"},
    "team": {"en": "Team", "es": "Equipo", "it": "Team"},
    "constructor": {"en": "Constructor", "es": "Constructor", "it": "Costruttore"},
    "year": {"en": "Year", "es": "Año", "it": "Anno"},
    "races": {"en": "Races", "es": "Carreras", "it": "Gare"},
    "sprints": {"en": "Sprints", "es": "Sprints", "it": "Sprint"},
    "time": {"en": "Time", "es": "Tiempo", "it": "Tempo"},
    "speed_kmh": {"en": "Speed (km/h)", "es": "Velocidad (km/h)", "it": "Velocità (km/h)"},
    "top_speed": {"en": "Top Speed", "es": "Velocidad máxima", "it": "Velocità Massima"},
    "gap": {"en": "Gap", "es": "Diferencia", "it": "Distacco"},
    "best_lap": {"en": "Best Lap", "es": "Mejor vuelta", "it": "Miglior Giro"},
    "finish_rate": {"en": "Finish Rate", "es": "Tasa de finalización", "it": "Tasso Completamento"},
    "avg_pos": {"en": "Avg Finish Pos", "es": "Pos. media", "it": "Pos. Media"},
    "nationality": {"en": "Nationality", "es": "Nacionalidad", "it": "Nazionalità"},
    "seasons": {"en": "Seasons", "es": "Temporadas", "it": "Stagioni"},
    "championships": {"en": "Championships", "es": "Campeonatos", "it": "Campionati"},
    "dnf": {"en": "DNF", "es": "DNF", "it": "DNF"},
    "dns": {"en": "DNS", "es": "DNS", "it": "DNS"},
    "finished": {"en": "Finished", "es": "Finalizado", "it": "Finito"},

    # --- Home page ---
    "home_title": {"en": "🏠 Database Overview", "es": "🏠 Resumen de la base de datos", "it": "🏠 Panoramica Database"},
    "home_seasons_range": {"en": "📅 Seasons", "es": "📅 Temporadas", "it": "📅 Stagioni"},
    "home_gp_count": {"en": "🏁 Grand Prix", "es": "🏁 Grandes Premios", "it": "🏁 Gran Premi"},
    "home_sessions_count": {"en": "📋 Sessions", "es": "📋 Sesiones", "it": "📋 Sessioni"},
    "home_riders_count": {"en": "🏍 Riders", "es": "🏍 Pilotos", "it": "🏍 Piloti"},
    "home_laps_count": {"en": "⏱ Lap Entries", "es": "⏱ Registros de vueltas", "it": "⏱ Giri Registrati"},
    "home_circuits_count": {"en": "🏟 Circuits", "es": "🏟 Circuitos", "it": "🏟 Circuiti"},
    "races_per_season": {"en": "Races per Season", "es": "Carreras por temporada", "it": "Gare per Stagione"},
    "laps_per_season": {"en": "Lap Data per Season", "es": "Datos de vueltas por temporada", "it": "Dati Giri per Stagione"},
    "laps_sector_per_season": {"en": "Laps & Sector Data per Season", "es": "Vueltas y datos de sectores por temporada", "it": "Giri e Dati Settore per Stagione"},
    "lap_entries": {"en": "Lap Entries", "es": "Registros de vueltas", "it": "Giri Registrati"},
    "top_riders_wins": {"en": "Top Riders by Race Wins", "es": "Pilotos con más victorias", "it": "Piloti per Vittorie"},
    "constructors_wins": {"en": "Constructors by Race Wins", "es": "Constructores por victorias", "it": "Costruttori per Vittorie"},
    "countries_visited": {"en": "Countries Visited", "es": "Países visitados", "it": "Paesi Visitati"},
    "sessions_by_type": {"en": "Sessions by Type", "es": "Sesiones por tipo", "it": "Sessioni per Tipo"},
    "data_source": {
        "en": "Data source: api.motogp.pulselive.com + resources.motogp.com (official timing PDFs)",
        "es": "Fuente: api.motogp.pulselive.com + resources.motogp.com (PDFs oficiales de cronometraje)",
        "it": "Fonte dati: api.motogp.pulselive.com + resources.motogp.com (PDF cronometraggio ufficiali)",
    },
    "data_quality_title": {
        "en": "📊 Data Quality & Coverage",
        "es": "📊 Calidad y cobertura de datos",
        "it": "📊 Qualità e copertura dati",
    },
    "data_quality_caption": {
        "en": "Classifications come from the API (available for all years). Lap and sector data is parsed from official timing PDFs (not available before 2007, limited for some older seasons).",
        "es": "Las clasificaciones provienen de la API (disponibles para todos los años). Los datos de vueltas y sectores se extraen de PDFs oficiales de cronometraje (no disponibles antes de 2007, limitados en temporadas más antiguas).",
        "it": "Le classifiche provengono dall'API (disponibili per tutti gli anni). I dati di giri e settori sono estratti dai PDF ufficiali di cronometraggio (non disponibili prima del 2007, limitati per alcune stagioni più vecchie).",
    },
    "classifications": {"en": "Classifications", "es": "Clasificaciones", "it": "Classifiche"},
    "lap_entries": {"en": "Lap entries", "es": "Registros de vueltas", "it": "Registri giri"},
    "sector_entries": {"en": "Sector entries", "es": "Registros de sectores", "it": "Registri settori"},
    "data_coverage_by_year": {
        "en": "Data coverage by season",
        "es": "Cobertura de datos por temporada",
        "it": "Copertura dati per stagione",
    },
    "records": {"en": "Records", "es": "Registros", "it": "Record"},

    # --- Pilot Rhythm ---
    "rhythm_title": {"en": "🎯 Pilot Rhythm — Best-N Lap Comparison", "es": "🎯 Ritmo de piloto — Comparación de N mejores vueltas", "it": "🎯 Ritmo Pilota — Confronto N Migliori Giri"},
    "rhythm_caption": {
        "en": "Each rider's N fastest laps. Cells colored 🟢 fastest → 🔴 slowest.",
        "es": "Las N vueltas más rápidas de cada piloto. Celdas coloreadas de 🟢 más rápido → 🔴 más lento.",
        "it": "I N giri più veloci di ogni pilota. Celle colorate da 🟢 più veloce → 🔴 più lento.",
    },
    "best_n_laps": {"en": "Best N laps", "es": "N mejores vueltas", "it": "N migliori giri"},
    "avg_best_laps": {
        "en": "Average of {n} Best Laps — Gap to Fastest",
        "es": "Promedio de las {n} mejores vueltas — Diferencia al más rápido",
        "it": "Media dei {n} Migliori Giri — Distacco dal Più Veloce",
    },

    # --- Lap Times ---
    "laptimes_title": {"en": "🏎 Lap Time Evolution", "es": "🏎 Evolución de tiempos por vuelta", "it": "🏎 Evoluzione Tempi sul Giro"},
    "lap_time_per_lap": {"en": "Lap Time per Lap", "es": "Tiempo por vuelta", "it": "Tempo per Giro"},
    "cumulative_gap": {"en": "Cumulative Gap to Virtual Leader", "es": "Diferencia acumulada al líder virtual", "it": "Distacco Cumulativo dal Leader Virtuale"},

    # --- Position Battle ---
    "position_title": {"en": "📍 Position Battle — Lap by Lap", "es": "📍 Batalla de posiciones — Vuelta a vuelta", "it": "📍 Battaglia Posizioni — Giro per Giro"},
    "position_caption": {
        "en": "Lap 0 = grid position (from qualifying). Subsequent laps derived from cumulative lap time.",
        "es": "Vuelta 0 = posición en parrilla (de clasificación). Vueltas siguientes derivadas del tiempo acumulado.",
        "it": "Giro 0 = posizione in griglia (dalle qualifiche). Giri successivi derivati dal tempo cumulativo.",
    },
    "position_per_lap": {"en": "Position per Lap", "es": "Posición por vuelta", "it": "Posizione per Giro"},

    # --- Classification ---
    "classification_title": {"en": "🏆 Classification", "es": "🏆 Clasificación", "it": "🏆 Classifica"},

    # --- Championship ---
    "championship_title": {"en": "🌍 Championship", "es": "🌍 Campeonato", "it": "🌍 Campionato"},
    "championship_caption": {
        "en": "Points accumulated after each race weekend (Race + Sprint).",
        "es": "Puntos acumulados después de cada fin de semana de carrera (carrera + Sprint).",
        "it": "Punti accumulati dopo ogni weekend di gara (Gara + Sprint).",
    },
    "championship_position_per_race": {"en": "Championship Position per Race", "es": "Posición en el campeonato por carrera", "it": "Posizione Campionato per Gara"},
    "cumulative_points": {"en": "Cumulative Points", "es": "Puntos acumulados", "it": "Punti Cumulativi"},
    "current_standings": {"en": "Current Standings", "es": "Clasificación actual", "it": "Classifica Attuale"},
    "show_top_n": {"en": "Show top N riders", "es": "Mostrar los N primeros pilotos", "it": "Mostra i primi N piloti"},

    # --- Reliability ---
    "reliability_title": {"en": "🔧 Reliability — Race Finishes vs DNFs", "es": "🔧 Fiabilidad — Finalizaciones vs abandonos", "it": "🔧 Affidabilità — Arrivi vs Ritiri"},
    "reliability_caption": {
        "en": "**DNF** = Did Not Finish (crashed or mechanical failure). **DNF Lap 1** = out on first lap. **DNS** = Did Not Start.",
        "es": "**DNF** = No finalizó (caída o fallo mecánico). **DNF Vuelta 1** = abandono en primera vuelta. **DNS** = No salió.",
        "it": "**DNF** = Non ha Finito (caduta o guasto meccanico). **DNF Giro 1** = uscito al primo giro. **DNS** = Non Partito.",
    },

    # --- No data / info messages ---
    "no_data": {"en": "No data", "es": "Sin datos", "it": "Nessun dato"},
    "no_data_load": {
        "en": "No data. Run `python load_to_sql.py --years 2021-2026`",
        "es": "Sin datos. Ejecute `python load_to_sql.py --years 2021-2026`",
        "it": "Nessun dato. Esegui `python load_to_sql.py --years 2021-2026`",
    },
    "no_events_for_year": {"en": "No events for {year}", "es": "No hay eventos para {year}", "it": "Nessun evento per {year}"},
    "no_sessions": {"en": "No sessions", "es": "No hay sesiones", "it": "Nessuna sessione"},
    "no_race_sprint_sessions": {"en": "No race/sprint sessions", "es": "No hay sesiones de carrera/sprint", "it": "Nessuna sessione gara/sprint"},
    "no_lap_data": {"en": "No lap data", "es": "No hay datos de vueltas", "it": "Nessun dato sui giri"},
    "no_position_data": {"en": "No position data", "es": "No hay datos de posición", "it": "Nessun dato posizione"},
    "no_race_lap_data": {"en": "No race lap data", "es": "No hay datos de vueltas de carrera", "it": "Nessun dato giri gara"},
    "not_enough_data": {"en": "Not enough data", "es": "No hay suficientes datos", "it": "Dati insufficienti"},
    "no_speed_data": {"en": "No speed data", "es": "No hay datos de velocidad", "it": "Nessun dato velocità"},
    "no_race_sprint_data_for_year": {"en": "No race/sprint data for {year}", "es": "No hay datos de carrera/sprint para {year}", "it": "Nessun dato gara/sprint per {year}"},
    "no_race_data_selected": {"en": "No race data for selected seasons", "es": "No hay datos de carrera para las temporadas seleccionadas", "it": "Nessun dato gara per le stagioni selezionate"},
    "no_grid_race_data": {"en": "No grid + race data available", "es": "No hay datos de parrilla + carrera disponibles", "it": "Nessun dato griglia + gara disponibile"},
    "no_race_data": {"en": "No race data", "es": "No hay datos de carrera", "it": "Nessun dato gara"},
    "no_riders": {"en": "No riders", "es": "No hay pilotos", "it": "Nessun pilota"},
    "no_data_for_pilot": {"en": "No data for {pilot}", "es": "No hay datos para {pilot}", "it": "Nessun dato per {pilot}"},
    "no_qualifying_data": {"en": "No qualifying data", "es": "No hay datos de clasificación", "it": "Nessun dato qualifiche"},
    "select_rider": {"en": "Select at least one rider", "es": "Seleccione al menos un piloto", "it": "Seleziona almeno un pilota"},
    "select_season": {"en": "Select at least one season", "es": "Seleccione al menos una temporada", "it": "Seleziona almeno una stagione"},

    # --- App title / page ---
    "page_title": {"en": "MotoGP Dashboard", "es": "Panel MotoGP", "it": "Dashboard MotoGP"},
    "app_title": {"en": "🏍 MotoGP Data Dashboard", "es": "🏍 Panel de datos MotoGP", "it": "🏍 Dashboard Dati MotoGP"},

    # --- Sidebar / context ---
    "air_label": {"en": "Air", "es": "Aire", "it": "Aria"},
    "track_label": {"en": "Track", "es": "Pista", "it": "Pista"},
    "all_sessions_label": {"en": "All Sessions", "es": "Todas las sesiones", "it": "Tutte le Sessioni"},
    "all_seasons_label": {"en": "All Seasons", "es": "Todas las temporadas", "it": "Tutte le Stagioni"},
    "all_gp_scope": {"en": "🏁 All Grand Prix — {scope}", "es": "🏁 Todos los Grandes Premios — {scope}", "it": "🏁 Tutti i Gran Premi — {scope}"},
    "seasons_in_db": {"en": "Seasons in database: {seasons}", "es": "Temporadas en la base de datos: {seasons}", "it": "Stagioni nel database: {seasons}"},

    # --- Home page metrics ---
    "metric_seasons": {"en": "🗓 Seasons", "es": "🗓 Temporadas", "it": "🗓 Stagioni"},
    "home_seasons_subheader": {"en": "📅 Seasons {min_year} — {max_year}", "es": "📅 Temporadas {min_year} — {max_year}", "it": "📅 Stagioni {min_year} — {max_year}"},

    # --- Lap Distribution ---
    "distribution_title": {"en": "📊 Lap Time Distribution", "es": "📊 Distribución de tiempos por vuelta", "it": "📊 Distribuzione Tempi sul Giro"},
    "distribution_caption": {
        "en": "How consistent is each rider? Narrow distributions = steady pace. Wide distributions = variable performance. Dots show individual laps.",
        "es": "¿Qué tan consistente es cada piloto? Distribuciones estrechas = ritmo estable. Distribuciones amplias = rendimiento variable. Los puntos muestran vueltas individuales.",
        "it": "Quanto è costante ogni pilota? Distribuzioni strette = ritmo costante. Distribuzioni ampie = prestazioni variabili. I punti mostrano i singoli giri.",
    },
    "chart_type": {"en": "Chart type", "es": "Tipo de gráfico", "it": "Tipo di grafico"},
    "chart_violin": {"en": "Violin", "es": "Violín", "it": "Violino"},
    "chart_box_strip": {"en": "Box + Strip", "es": "Box + strip", "it": "Box + Strip"},
    "chart_ridge": {"en": "Ridge (Histogram)", "es": "Ridge (histograma)", "it": "Ridge (Istogramma)"},
    "violin_explanation": {
        "en": "The **violin plot** shows the distribution of lap times for each rider. The wider the shape at a given time, the more laps were completed near that pace. A **tall, narrow violin** means the rider was very consistent. A **wide, spread-out violin** means lap times varied a lot. The **white box** inside shows the middle 50% of lap times, the **horizontal line** inside the box is the median (typical) lap, and the **dots** are individual laps.",
        "es": "El **gráfico de violín** muestra la distribución de los tiempos por vuelta de cada piloto. Cuanto más ancha es la forma en un tiempo dado, más vueltas se completaron cerca de ese ritmo. Un **violín alto y estrecho** significa que el piloto fue muy consistente. Un **violín ancho y disperso** significa que los tiempos variaron mucho. La **caja blanca** interior muestra el 50% central de los tiempos, la **línea horizontal** dentro de la caja es la mediana (vuelta típica) y los **puntos** son vueltas individuales.",
        "it": "Il **grafico a violino** mostra la distribuzione dei tempi sul giro per ogni pilota. Più la forma è larga a un dato tempo, più giri sono stati completati a quel ritmo. Un **violino alto e stretto** indica grande costanza. Un **violino largo e sparso** indica tempi molto variabili. La **casella bianca** interna mostra il 50% centrale dei tempi, la **linea orizzontale** nella casella è la mediana (giro tipico) e i **punti** sono i singoli giri.",
    },
    "violin_plot_title": {"en": "Lap Time Distribution (Violin Plot)", "es": "Distribución de tiempos (gráfico de violín)", "it": "Distribuzione Tempi (Grafico a Violino)"},
    "box_explanation": {
        "en": "The **box plot** summarizes each rider's lap times. The **box** spans from the 25th to the 75th percentile (the middle half of all laps). The **line in the middle** of the box is the median lap time. The **whiskers** extend to the fastest and slowest non-outlier laps. Each **dot** is an individual lap — clusters of dots show where the rider spent most of their time.",
        "es": "El **diagrama de caja** resume los tiempos de cada piloto. La **caja** abarca del percentil 25 al 75 (la mitad central de todas las vueltas). La **línea central** de la caja es el tiempo mediano. Los **bigotes** se extienden hasta las vueltas más rápidas y lentas sin atípicos. Cada **punto** es una vuelta individual — las agrupaciones muestran dónde pasó más tiempo el piloto.",
        "it": "Il **box plot** riassume i tempi di ogni pilota. La **casella** va dal 25° al 75° percentile (la metà centrale di tutti i giri). La **linea centrale** è il tempo mediano. I **baffi** si estendono ai giri più veloci e lenti non anomali. Ogni **punto** è un singolo giro — i raggruppamenti mostrano dove il pilota ha trascorso più tempo.",
    },
    "box_strip_title": {"en": "Lap Time Distribution (Box + Strip Plot)", "es": "Distribución de tiempos (box + strip)", "it": "Distribuzione Tempi (Box + Strip)"},
    "ridge_explanation": {
        "en": "The **ridge plot** stacks each rider's lap time distribution horizontally. The **peaks** show the most common lap times — a single sharp peak means the rider was very consistent, while multiple peaks or a flat shape indicate variable pace (e.g., different tyre stints or changing conditions). The **dashed line** marks the mean (average) lap time.",
        "es": "El **gráfico ridge** apila horizontalmente la distribución de tiempos de cada piloto. Los **picos** muestran los tiempos más comunes — un pico agudo único significa alta consistencia, mientras que múltiples picos o forma plana indican ritmo variable (p.ej., diferentes stints de neumáticos o condiciones cambiantes). La **línea discontinua** marca el tiempo medio.",
        "it": "Il **grafico ridge** sovrappone orizzontalmente la distribuzione dei tempi di ogni pilota. I **picchi** mostrano i tempi più frequenti — un singolo picco netto indica grande costanza, mentre picchi multipli o forma piatta indicano ritmo variabile (es. stint diversi o condizioni mutevoli). La **linea tratteggiata** segna il tempo medio.",
    },
    "ridge_plot_title": {"en": "Lap Time Ridge Plot", "es": "Gráfico ridge de tiempos", "it": "Grafico Ridge dei Tempi"},
    "lap_time_s": {"en": "Lap Time (s)", "es": "Tiempo por vuelta (s)", "it": "Tempo sul Giro (s)"},
    "time_s": {"en": "Time (s)", "es": "Tiempo (s)", "it": "Tempo (s)"},
    "consistency_stats": {"en": "Consistency Statistics", "es": "Estadísticas de consistencia", "it": "Statistiche di Costanza"},
    "consistency_explanation": {
        "en": "Key numbers for each rider's lap times: **Median** = the middle lap time (half the laps were faster, half slower). **Std Dev** = standard deviation — a measure of how much lap times vary (lower = more consistent). **Range** = difference between fastest and slowest lap.",
        "es": "Números clave para los tiempos de cada piloto: **Mediana** = el tiempo central (la mitad de las vueltas fueron más rápidas, la otra mitad más lentas). **Desv. Est.** = desviación estándar — medida de la variación de los tiempos (menor = más consistente). **Rango** = diferencia entre la vuelta más rápida y la más lenta.",
        "it": "Numeri chiave per i tempi di ogni pilota: **Mediana** = il tempo centrale (metà giri più veloci, metà più lenti). **Dev. Std.** = deviazione standard — misura della variazione dei tempi (minore = più costante). **Range** = differenza tra il giro più veloce e il più lento.",
    },
    "sector_clustering": {"en": "Sector Time Clustering", "es": "Agrupación de tiempos por sector", "it": "Raggruppamento Tempi Settore"},
    "sector_clustering_explanation": {
        "en": "Each **dot** represents one lap's time through a specific sector of the circuit. A **tight cluster** of dots means the rider is very consistent in that sector. **Spread-out dots** mean the rider's time varies — possibly due to mistakes, traffic, or tyre degradation. Compare riders to see who is strongest in each sector.",
        "es": "Cada **punto** representa el tiempo de una vuelta en un sector específico del circuito. Un **grupo compacto** de puntos significa que el piloto es muy consistente en ese sector. **Puntos dispersos** indican tiempos variables — posiblemente por errores, tráfico o degradación de neumáticos. Compare pilotos para ver quién es más fuerte en cada sector.",
        "it": "Ogni **punto** rappresenta il tempo di un giro in un settore specifico del circuito. Un **gruppo compatto** di punti indica grande costanza in quel settore. **Punti sparsi** indicano tempi variabili — probabilmente per errori, traffico o degrado gomme. Confronta i piloti per vedere chi è più forte in ogni settore.",
    },
    "sector_label": {"en": "Sector", "es": "Sector", "it": "Settore"},
    "sector_time_distribution": {"en": "Sector {num} Time Distribution", "es": "Distribución de tiempos del sector {num}", "it": "Distribuzione Tempi Settore {num}"},
    "sector_time_s": {"en": "{sector} Time (s)", "es": "Tiempo {sector} (s)", "it": "Tempo {sector} (s)"},

    # --- Sector Heatmap ---
    "sector_analysis_title": {"en": "⏱ Sector Time Analysis", "es": "⏱ Análisis de tiempos por sector", "it": "⏱ Analisi Tempi Settore"},
    "best_sector_times_delta": {"en": "Best Sector Times (delta from fastest)", "es": "Mejores tiempos por sector (delta del más rápido)", "it": "Migliori Tempi Settore (delta dal più veloce)"},
    "ideal_vs_actual": {"en": "Ideal Lap vs Actual Best Lap", "es": "Vuelta ideal vs mejor vuelta real", "it": "Giro Ideale vs Miglior Giro Reale"},

    # --- Tyre Degradation ---
    "tyre_degradation_title": {"en": "🛞 Tyre Degradation Curves", "es": "🛞 Curvas de degradación de neumáticos", "it": "🛞 Curve Degrado Gomme"},
    "lap_time_vs_tyre": {"en": "Lap Time vs Laps on Tyre", "es": "Tiempo por vuelta vs vueltas con el neumático", "it": "Tempo sul Giro vs Giri con la Gomma"},
    "laps_on_tyre": {"en": "Laps on Tyre", "es": "Vueltas con el neumático", "it": "Giri con la Gomma"},

    # --- Tyre Whisperers ---
    "tyre_whisperer_header": {"en": "🧙 Tyre Whisperers — {year}", "es": "🧙 Susurradores de neumáticos — {year}", "it": "🧙 Sussurratori di Gomme — {year}"},
    "tyre_whisperer_caption": {
        "en": "**Who manages tyres best during a race?** For each race, we compare each rider's lap time in the first third of the race vs the last third. A rider who loses less time (or even gains) relative to the field average is a better tyre manager. The **Tyre Whisperer Score** = how much less degradation (in seconds/lap) a rider has compared to the field average. Positive = better than average tyre management.",
        "es": "**¿Quién gestiona mejor los neumáticos durante una carrera?** para cada carrera, comparamos el tiempo por vuelta de cada piloto en el primer tercio vs el último tercio. Un piloto que pierde menos tiempo (o incluso gana) en relación al promedio del campo es mejor gestor de neumáticos. El **Tyre Whisperer Score** = cuánta menos degradación (en segundos/vuelta) tiene un piloto respecto al promedio. Positivo = mejor gestión que el promedio.",
        "it": "**Chi gestisce meglio le gomme durante una gara?** Per ogni gara, confrontiamo il tempo sul giro di ogni pilota nel primo terzo vs l'ultimo terzo. Un pilota che perde meno tempo (o addirittura guadagna) rispetto alla media del campo è un miglior gestore di gomme. Il **Tyre Whisperer Score** = quanta meno degradazione (in secondi/giro) ha un pilota rispetto alla media. Positivo = gestione superiore alla media.",
    },
    "tyre_whisperer_ranking": {"en": "Season Tyre Whisperer Ranking", "es": "Ranking de susurradores de la temporada", "it": "Classifica Sussurratori della Stagione"},
    "tyre_whisperer_score_title": {
        "en": "{year} Tyre Whisperer Score (avg seconds/lap better than field)",
        "es": "{year} Tyre Whisperer Score (promedio segundos/vuelta mejor que el campo)",
        "it": "{year} Tyre Whisperer Score (media secondi/giro meglio del campo)",
    },
    "advantage_s_lap": {"en": "Advantage (s/lap)", "es": "Ventaja (s/vuelta)", "it": "Vantaggio (s/giro)"},
    "per_race_tyre_advantage": {"en": "Per-Race Tyre Management Advantage", "es": "Ventaja de gestión de neumáticos por carrera", "it": "Vantaggio Gestione Gomme per Gara"},
    "tyre_advantage_caption": {
        "en": "Green = less degradation than the field. Red = more degradation. Values in seconds/lap.",
        "es": "Verde = menos degradación que el campo. Rojo = más degradación. Valores en segundos/vuelta.",
        "it": "Verde = meno degrado del campo. Rosso = più degrado. Valori in secondi/giro.",
    },
    "detailed_scores": {"en": "Detailed Scores", "es": "Puntuaciones detalladas", "it": "Punteggi Dettagliati"},
    "tyre_advantage_col": {"en": "Tyre Advantage (s/lap)", "es": "Ventaja neumáticos (s/vuelta)", "it": "Vantaggio Gomme (s/giro)"},
    "avg_degradation_col": {"en": "Avg Degradation (s/lap)", "es": "Degradación media (s/vuelta)", "it": "Degrado Medio (s/giro)"},
    "how_calculated": {"en": "How is this calculated?", "es": "¿Cómo se calcula?", "it": "Come viene calcolato?"},
    "tyre_calculation_explanation": {
        "en": """**For each race:**
1. Split each rider's laps into first ⅓ and last ⅓
2. Calculate **degradation** = avg lap time (last ⅓) − avg lap time (first ⅓)
3. Calculate **field average degradation** across all riders in that race
4. **Advantage** = field avg degradation − rider's degradation

**A positive advantage means the rider's tyres degraded less than the average rider** —
they were faster relative to the field in the closing laps.

**Season score** = average advantage across all races (minimum 3 races required).

*Outlier laps (>10% slower than rider's median) are excluded to filter crashes/incidents.*""",
        "es": """**Para cada carrera:**
1. Dividir las vueltas de cada piloto en primer ⅓ y último ⅓
2. Calcular **degradación** = tiempo medio (último ⅓) − tiempo medio (primer ⅓)
3. Calcular **degradación media del campo** entre todos los pilotos en esa carrera
4. **Ventaja** = degradación media del campo − degradación del piloto

**Una ventaja positiva significa que los neumáticos del piloto se degradaron menos que el promedio** —
fue más rápido relativo al campo en las últimas vueltas.

**Puntuación de temporada** = ventaja media en todas las carreras (mínimo 3 carreras requeridas).

*Vueltas atípicas (>10% más lentas que la mediana del piloto) se excluyen para filtrar caídas/incidentes.*""",
        "it": """**Per ogni gara:**
1. Dividere i giri di ogni pilota in primo ⅓ e ultimo ⅓
2. Calcolare **degrado** = tempo medio (ultimo ⅓) − tempo medio (primo ⅓)
3. Calcolare **degrado medio del campo** tra tutti i piloti in quella gara
4. **Vantaggio** = degrado medio del campo − degrado del pilota

**Un vantaggio positivo significa che le gomme del pilota si sono degradate meno della media** —
era più veloce rispetto al campo negli ultimi giri.

**Punteggio stagionale** = vantaggio medio in tutte le gare (minimo 3 gare richieste).

*Giri anomali (>10% più lenti della mediana del pilota) sono esclusi per filtrare cadute/incidenti.*""",
    },

    # --- Speed Trap ---
    "speed_trap_title": {"en": "⚡ Speed Trap Analysis", "es": "⚡ Análisis de trampa de velocidad", "it": "⚡ Analisi Speed Trap"},
    "riders_leave_empty": {"en": "Riders (leave empty for all)", "es": "Pilotos (dejar vacío para todos)", "it": "Piloti (lascia vuoto per tutti)"},
    "max_speed_per_rider": {"en": "Maximum Speed per Rider", "es": "Velocidad máxima por piloto", "it": "Velocità Massima per Pilota"},
    "speed_distribution": {"en": "Speed Distribution", "es": "Distribución de velocidad", "it": "Distribuzione Velocità"},
    "speed_across_gp": {"en": "Speed across Grand Prix", "es": "Velocidad en los Grandes Premios", "it": "Velocità nei Gran Premi"},
    "speed_per_lap": {"en": "Speed per Lap", "es": "Velocidad por vuelta", "it": "Velocità per Giro"},
    "kmh": {"en": "km/h", "es": "km/h", "it": "km/h"},

    # --- Classification ---
    "classification_header": {"en": "🏆 Classification — {session}", "es": "🏆 Clasificación — {session}", "it": "🏆 Classifica — {session}"},

    # --- Championship ---
    "championship_header": {"en": "🌍 {year} Championship", "es": "🌍 Campeonato {year}", "it": "🌍 Campionato {year}"},
    "championship_pos_title": {
        "en": "{year} Championship Position after Each Race",
        "es": "Posición en el campeonato {year} tras cada carrera",
        "it": "Posizione Campionato {year} dopo Ogni Gara",
    },
    "championship_pts_title": {
        "en": "{year} Cumulative Championship Points",
        "es": "Puntos acumulados del campeonato {year}",
        "it": "Punti Cumulativi Campionato {year}",
    },
    "grand_prix_label": {"en": "Grand Prix", "es": "Gran Premio", "it": "Gran Premio"},
    "championship_position_label": {"en": "Championship Position", "es": "Posición en el campeonato", "it": "Posizione Campionato"},

    # --- Reliability ---
    "reliability_caption_text": {
        "en": "**DNF** = Did Not Finish (rider started but crashed or had a mechanical failure). **DNF Lap 1** = crashed/out on the first lap. **DNS** = Did Not Start (rider was entered but didn't take the start).",
        "es": "**DNF** = No finalizó (el piloto salió pero cayó o tuvo un fallo mecánico). **DNF Vuelta 1** = caída/abandono en la primera vuelta. **DNS** = No salió (el piloto estaba inscrito pero no tomó la salida).",
        "it": "**DNF** = Non ha Finito (il pilota è partito ma è caduto o ha avuto un guasto meccanico). **DNF Giro 1** = caduta/uscita al primo giro. **DNS** = Non Partito (il pilota era iscritto ma non ha preso il via).",
    },
    "race_outcomes_title": {
        "en": "Race Outcomes ({years})",
        "es": "Resultados de carreras ({years})",
        "it": "Risultati Gare ({years})",
    },
    "outcome": {"en": "Outcome", "es": "Resultado", "it": "Risultato"},
    "finish_rate_by_season": {"en": "Finish Rate by Season", "es": "Tasa de finalización por temporada", "it": "Tasso Completamento per Stagione"},
    "finish_rate_heatmap_title": {
        "en": "Finish Rate % by Season (🟢 100% → 🔴 0%)",
        "es": "Tasa de finalización % por temporada (🟢 100% → 🔴 0%)",
        "it": "Tasso Completamento % per Stagione (🟢 100% → 🔴 0%)",
    },

    # --- Teams & Constructors ---
    "teams_constructors_header": {"en": "🏢 Teams & Constructors — {year}", "es": "🏢 Equipos y constructores — {year}", "it": "🏢 Team e Costruttori — {year}"},
    "view_label": {"en": "View", "es": "Vista", "it": "Vista"},
    "teams_label": {"en": "Teams", "es": "Equipos", "it": "Team"},
    "constructors_label": {"en": "Constructors", "es": "Constructores", "it": "Costruttori"},
    "team_performance": {"en": "Team Performance (Sum of Rider Points)", "es": "Rendimiento de equipos (suma de puntos de pilotos)", "it": "Prestazioni Team (Somma Punti Piloti)"},
    "team_points_title": {"en": "{year} Team Points (rider breakdown)", "es": "Puntos de equipos {year} (desglose por piloto)", "it": "Punti Team {year} (dettaglio piloti)"},
    "total_points_label": {"en": "Total Points", "es": "Puntos totales", "it": "Punti Totali"},
    "team_progression": {"en": "Team Championship Progression", "es": "Progresión del campeonato de equipos", "it": "Progressione Campionato Team"},
    "team_pts_progression_title": {"en": "{year} Team Points Progression", "es": "Progresión de puntos de equipos {year}", "it": "Progressione Punti Team {year}"},
    "cumulative_points_label": {"en": "Cumulative Points", "es": "Puntos acumulados", "it": "Punti Cumulativi"},
    "team_standings": {"en": "Team Standings", "es": "Clasificación de equipos", "it": "Classifica Team"},
    "constructor_performance": {"en": "Constructor Performance (Average Points per Rider)", "es": "Rendimiento de constructores (media de puntos por piloto)", "it": "Prestazioni Costruttori (Media Punti per Pilota)"},
    "constructor_performance_caption": {
        "en": "Average points per rider — fair comparison across constructors with different number of riders.",
        "es": "Media de puntos por piloto — comparación justa entre constructores con diferente número de pilotos.",
        "it": "Media punti per pilota — confronto equo tra costruttori con diverso numero di piloti.",
    },
    "avg_points_per_rider": {"en": "Avg Points per Rider", "es": "Media de puntos por piloto", "it": "Media Punti per Pilota"},
    "total_points_all_riders": {"en": "Total Points (all riders)", "es": "Puntos totales (todos los pilotos)", "it": "Punti Totali (tutti i piloti)"},
    "rider_points_by_constructor": {"en": "Rider Points by Constructor", "es": "Puntos de pilotos por constructor", "it": "Punti Piloti per Costruttore"},
    "constructor_points_breakdown": {"en": "{year} Constructor Points — Rider Breakdown", "es": "Puntos constructor {year} — Desglose por piloto", "it": "Punti Costruttore {year} — Dettaglio Piloti"},
    "constructor_avg_across_seasons": {"en": "Constructor Avg Points per Rider — Across Seasons", "es": "Media de puntos por piloto del constructor — A lo largo de las temporadas", "it": "Media Punti per Pilota del Costruttore — Nelle Stagioni"},
    "constructor_avg_yoy_title": {"en": "Constructor Avg Points per Rider — Year over Year", "es": "Media de puntos por piloto del constructor — Año tras año", "it": "Media Punti per Pilota Costruttore — Anno per Anno"},
    "avg_pts_rider_label": {"en": "Avg Points/Rider", "es": "Media puntos/Piloto", "it": "Media Punti/Pilota"},
    "constructor_summary": {"en": "Constructor Summary", "es": "Resumen de constructores", "it": "Riepilogo Costruttori"},

    # --- Grid Advantage ---
    "grid_advantage_header": {"en": "🏁 Grid Advantage — Does Starting Position Matter?", "es": "🏁 Ventaja de parrilla — ¿Importa la posición de salida?", "it": "🏁 Vantaggio Griglia — Conta la Posizione di Partenza?"},
    "grid_advantage_caption": {
        "en": "What percentage of riders starting from the first Y grid positions finish in the top X? Grid position = Q2 qualifying result.",
        "es": "¿Qué porcentaje de pilotos que salen de las primeras Y posiciones de parrilla terminan en el top X? Posición de parrilla = resultado de Q2.",
        "it": "Quale percentuale di piloti partendo dalle prime Y posizioni in griglia arriva nella top X? Posizione in griglia = risultato qualifiche Q2.",
    },
    "race_type_label": {"en": "Race type", "es": "Tipo de carrera", "it": "Tipo di gara"},
    "main_race": {"en": "Main Race", "es": "Carrera principal", "it": "Gara Principale"},
    "sprint_race": {"en": "Sprint Race", "es": "Carrera Sprint", "it": "Gara Sprint"},
    "both": {"en": "Both", "es": "Ambas", "it": "Entrambe"},
    "finish_top_x": {"en": "Finish in top X positions", "es": "Terminar en las X primeras posiciones", "it": "Arrivare nelle prime X posizioni"},
    "starting_from_y": {"en": "Starting from first Y grid positions", "es": "Saliendo de las primeras Y posiciones de parrilla", "it": "Partendo dalle prime Y posizioni in griglia"},
    "grid_pct_of_riders": {
        "en": "of riders starting from <b>top {max_y}</b> grid positions finished in the <b>top {top_x}</b>",
        "es": "de los pilotos saliendo del <b>top {max_y}</b> de parrilla terminaron en el <b>top {top_x}</b>",
        "it": "dei piloti partendo dal <b>top {max_y}</b> della griglia hanno chiuso nella <b>top {top_x}</b>",
    },
    "grid_pct_starts": {"en": "({count} out of {total} starts)", "es": "({count} de {total} salidas)", "it": "({count} su {total} partenze)"},
    "grid_pct_title": {
        "en": "% of riders finishing top {top_x} when starting from top Y grid positions",
        "es": "% de pilotos terminando en top {top_x} saliendo de las primeras Y posiciones de parrilla",
        "it": "% dei piloti che chiudono nella top {top_x} partendo dalle prime Y posizioni in griglia",
    },
    "finished_top_x_pct": {"en": "Finished top {top_x} %", "es": "Terminaron top {top_x} %", "it": "Chiuso top {top_x} %"},
    "grid_finish_frequency": {"en": "Grid Position → Finish Position (Frequency)", "es": "Posición de parrilla → Posición final (frecuencia)", "it": "Posizione Griglia → Posizione Finale (Frequenza)"},
    "grid_finish_frequency_caption": {
        "en": "How often does each grid position lead to each finish position? Darker = more frequent.",
        "es": "¿Con qué frecuencia cada posición de parrilla lleva a cada posición final? Más oscuro = más frecuente.",
        "it": "Con che frequenza ogni posizione in griglia porta a ogni posizione finale? Più scuro = più frequente.",
    },
    "grid_vs_finish_freq_title": {"en": "Grid Position vs Finish Position (frequency)", "es": "Posición de parrilla vs posición final (frecuencia)", "it": "Posizione Griglia vs Posizione Finale (frequenza)"},
    "finish_position": {"en": "Finish Position", "es": "Posición final", "it": "Posizione Finale"},
    "grid_position": {"en": "Grid Position", "es": "Posición de parrilla", "it": "Posizione in Griglia"},
    "conversion_rate_subheader": {"en": "Top Y Grid → Top X Finish (Conversion Rate %)", "es": "Top Y parrilla → Top X final (tasa de conversión %)", "it": "Top Y Griglia → Top X Finale (Tasso Conversione %)"},
    "conversion_rate_caption": {
        "en": "For each combination of 'starting from top Y' and 'finishing in top X', what is the conversion rate?",
        "es": "Para cada combinación de 'saliendo del top Y' y 'terminando en el top X', ¿cuál es la tasa de conversión?",
        "it": "Per ogni combinazione di 'partendo dalla top Y' e 'chiudendo nella top X', qual è il tasso di conversione?",
    },
    "conversion_rate_title": {"en": "Conversion Rate: Starting from Top Y → Finishing in Top X", "es": "Tasa de conversión: Saliendo del top Y → Terminando en el top X", "it": "Tasso Conversione: Partendo dalla Top Y → Chiudendo nella Top X"},
    "finish_pos_top_x": {"en": "Finish Position (top X)", "es": "Posición final (top X)", "it": "Posizione Finale (top X)"},
    "grid_pos_top_y": {"en": "Grid Position (top Y)", "es": "Posición de parrilla (top Y)", "it": "Posizione Griglia (top Y)"},
    "grid_trend_subheader": {"en": "Grid Advantage Trend Over Seasons", "es": "Tendencia de ventaja de parrilla por temporada", "it": "Tendenza Vantaggio Griglia nelle Stagioni"},
    "grid_trend_caption": {
        "en": "% of top-3 grid starters finishing in top {top_x} — is pole becoming more/less decisive?",
        "es": "% de los que salen del top-3 de parrilla terminando en top {top_x} — ¿la pole es cada vez más/menos decisiva?",
        "it": "% di partenti dalla top-3 in griglia che chiudono nella top {top_x} — la pole diventa più/meno decisiva?",
    },
    "front_row_conversion_title": {"en": "Front Row → Top {top_x} Conversion Rate by Season", "es": "Primera fila → Top {top_x} tasa de conversión por temporada", "it": "Prima Fila → Top {top_x} Tasso Conversione per Stagione"},

    # --- Circuits ---
    "circuit_analysis_header": {"en": "🏟 Circuit Analysis", "es": "🏟 Análisis de circuitos", "it": "🏟 Analisi Circuiti"},
    "circuit_label": {"en": "Circuit", "es": "Circuito", "it": "Circuito"},
    "races_in_db": {"en": "Races in DB", "es": "Carreras en BD", "it": "Gare nel DB"},
    "different_winners": {"en": "Different Winners", "es": "Ganadores diferentes", "it": "Vincitori Diversi"},
    "winning_constructors": {"en": "Winning Constructors", "es": "Constructores ganadores", "it": "Costruttori Vincitori"},
    "top_winners_riders": {"en": "Top Winners (Riders)", "es": "Más victorias (pilotos)", "it": "Più Vittorie (Piloti)"},
    "top_winners_constructors": {"en": "Top Winners (Constructors)", "es": "Más victorias (constructores)", "it": "Più Vittorie (Costruttori)"},
    "race_winners_by_year": {"en": "Race Winners by Year", "es": "Ganadores de carrera por año", "it": "Vincitori di Gara per Anno"},
    "most_podiums_circuit": {"en": "Most Podiums at this Circuit", "es": "Más podios en este circuito", "it": "Più Podi in questo Circuito"},
    "podiums_circuit_title": {"en": "Podiums at this Circuit", "es": "Podios en este circuito", "it": "Podi in questo Circuito"},
    "winning_pace_evolution": {"en": "Winning Pace Evolution", "es": "Evolución del ritmo ganador", "it": "Evoluzione Ritmo Vincente"},
    "winner_best_lap_title": {"en": "Winner's Best Lap Time by Year", "es": "Mejor vuelta del ganador por año", "it": "Miglior Giro del Vincitore per Anno"},
    "best_lap_s": {"en": "Best Lap (s)", "es": "Mejor vuelta (s)", "it": "Miglior Giro (s)"},
    "top_speed_circuit": {"en": "Top Speed at this Circuit", "es": "Velocidad máxima en este circuito", "it": "Velocità Massima in questo Circuito"},
    "max_speed_trace": {"en": "Max Speed", "es": "Velocidad máxima", "it": "Velocità Massima"},
    "avg_speed_trace": {"en": "Avg Speed", "es": "Velocidad media", "it": "Velocità Media"},
    "top_speed_evolution_title": {"en": "Top Speed Evolution (Race)", "es": "Evolución de velocidad máxima (carrera)", "it": "Evoluzione Velocità Massima (Gara)"},
    "total_points_circuit": {"en": "Total Points Scored at this Circuit", "es": "Puntos totales en este circuito", "it": "Punti Totali in questo Circuito"},
    "circuit_competitiveness": {"en": "Circuit Competitiveness", "es": "Competitividad del circuito", "it": "Competitività del Circuito"},
    "repeat_winners_pct": {"en": "Repeat Winners %", "es": "% Ganadores repetidos", "it": "% Vincitori Ripetuti"},
    "repeat_winners_help": {"en": "% of riders who have won here more than once", "es": "% de pilotos que han ganado aquí más de una vez", "it": "% dei piloti che hanno vinto qui più di una volta"},
    "different_podium_riders": {"en": "Different Podium Riders", "es": "Pilotos diferentes en podio", "it": "Piloti Diversi sul Podio"},

    # --- Pilot Rankings ---
    "pilot_rankings_header": {"en": "🏅 Pilot Rankings", "es": "🏅 Ranking de pilotos", "it": "🏅 Classifica Piloti"},
    "pilot_rankings_caption": {"en": "All-time pilot statistics across all loaded seasons in the database.", "es": "Estadísticas históricas de pilotos en todas las temporadas cargadas en la base de datos.", "it": "Statistiche storiche dei piloti in tutte le stagioni caricate nel database."},
    "rank_by": {"en": "Rank by", "es": "Ordenar por", "it": "Ordina per"},
    "ranking_championships_won": {"en": "Championships Won", "es": "Campeonatos ganados", "it": "Campionati Vinti"},
    "ranking_race_wins": {"en": "Race Wins", "es": "Victorias en carrera", "it": "Vittorie in Gara"},
    "ranking_sprint_wins": {"en": "Sprint Wins", "es": "Victorias en Sprint", "it": "Vittorie Sprint"},
    "ranking_total_wins": {"en": "Total Wins (Race + Sprint)", "es": "Victorias totales (carrera + Sprint)", "it": "Vittorie Totali (Gara + Sprint)"},
    "ranking_race_podiums": {"en": "Race Podiums", "es": "Podios en carrera", "it": "Podi in Gara"},
    "ranking_pole_positions": {"en": "Pole Positions", "es": "Pole Positions", "it": "Pole Position"},
    "ranking_total_points": {"en": "Total Points", "es": "Puntos totales", "it": "Punti Totali"},
    "ranking_points_efficiency": {"en": "Points Efficiency %", "es": "Eficiencia de puntos %", "it": "Efficienza Punti %"},
    "ranking_win_rate": {"en": "Win Rate %", "es": "Tasa de victorias %", "it": "Tasso Vittorie %"},
    "ranking_podium_rate": {"en": "Podium Rate %", "es": "Tasa de podios %", "it": "Tasso Podi %"},
    "ranking_race_starts": {"en": "Race Starts", "es": "Salidas de carrera", "it": "Partenze Gara"},
    "ranking_finish_rate": {"en": "Finish Rate %", "es": "Tasa de finalización %", "it": "Tasso Completamento %"},
    "ranking_desc_championships": {
        "en": "Number of seasons where the rider finished with the most points (Race + Sprint combined).",
        "es": "Número de temporadas en las que el piloto terminó con más puntos (carrera + Sprint combinados).",
        "it": "Numero di stagioni in cui il pilota ha chiuso con più punti (Gara + Sprint combinati).",
    },
    "ranking_desc_race_wins": {
        "en": "Total number of main race victories (Sunday races).",
        "es": "Número total de victorias en carreras principales (carreras del domingo).",
        "it": "Numero totale di vittorie in gara principale (gare della domenica).",
    },
    "ranking_desc_sprint_wins": {
        "en": "Total number of sprint race victories (Saturday short races, introduced in 2023).",
        "es": "Número total de victorias en sprint (carreras cortas del sábado, desde 2023).",
        "it": "Numero totale di vittorie sprint (gare corte del sabato, introdotte nel 2023).",
    },
    "ranking_desc_total_wins": {
        "en": "Combined total of main race and sprint race victories.",
        "es": "Total combinado de victorias en carrera principal y sprint.",
        "it": "Totale combinato di vittorie in gara principale e sprint.",
    },
    "ranking_desc_race_podiums": {
        "en": "Total number of top-3 finishes in main races (1st, 2nd, or 3rd).",
        "es": "Número total de top-3 en carreras principales (1º, 2º o 3º).",
        "it": "Numero totale di top-3 in gare principali (1°, 2° o 3°).",
    },
    "ranking_desc_poles": {
        "en": "Number of times the rider qualified in P1 (fastest in Q2). Starting from the front of the grid.",
        "es": "Número de veces que el piloto clasificó P1 (más rápido en Q2). saliendo desde el frente de la parrilla.",
        "it": "Numero di volte in cui il pilota si è qualificato P1 (più veloce in Q2). Partendo dalla prima posizione.",
    },
    "ranking_desc_total_points": {
        "en": "Total championship points scored across all races and sprints.",
        "es": "Puntos totales de campeonato en todas las carreras y sprints.",
        "it": "Punti campionato totali in tutte le gare e sprint.",
    },
    "ranking_desc_points_efficiency": {
        "en": "Percentage of the **maximum possible points** the rider could have scored. Calculated as: actual points ÷ (races × 25 + sprints × 12) × 100. A rider who wins every race and sprint scores 100%. Minimum 10 race starts required.",
        "es": "Porcentaje de los **puntos máximos posibles** que el piloto podría haber obtenido. Calculado como: puntos reales ÷ (carreras × 25 + sprints × 12) × 100. Un piloto que gana todas las carreras y sprints obtiene 100%. Mínimo 10 salidas de carrera requeridas.",
        "it": "Percentuale dei **punti massimi possibili** che il pilota avrebbe potuto ottenere. Calcolato come: punti effettivi ÷ (gare × 25 + sprint × 12) × 100. Un pilota che vince ogni gara e sprint ottiene 100%. Minimo 10 partenze gara richieste.",
    },
    "ranking_desc_win_rate": {
        "en": "Percentage of main races won out of all main races started. Minimum 10 race starts required.",
        "es": "Porcentaje de carreras principales ganadas del total de carreras iniciadas. Mínimo 10 salidas requeridas.",
        "it": "Percentuale di gare principali vinte sul totale di gare iniziate. Minimo 10 partenze richieste.",
    },
    "ranking_desc_podium_rate": {
        "en": "Percentage of main races finished on the podium (top 3) out of all main races started. Minimum 10 race starts required.",
        "es": "Porcentaje de carreras principales terminadas en el podio (top 3) del total de carreras iniciadas. Mínimo 10 salidas requeridas.",
        "it": "Percentuale di gare principali finite sul podio (top 3) sul totale di gare iniziate. Minimo 10 partenze richieste.",
    },
    "ranking_desc_race_starts": {
        "en": "Total number of main races the rider has participated in.",
        "es": "Número total de carreras principales en las que ha participado el piloto.",
        "it": "Numero totale di gare principali a cui il pilota ha partecipato.",
    },
    "ranking_desc_finish_rate": {
        "en": "Percentage of main races where the rider crossed the finish line (not DNF/DNS). Higher = more reliable. Minimum 10 race starts required.",
        "es": "Porcentaje de carreras principales donde el piloto cruzó la línea de meta (sin DNF/DNS). Mayor = más fiable. Mínimo 10 salidas requeridas.",
        "it": "Percentuale di gare principali in cui il pilota ha tagliato il traguardo (non DNF/DNS). Più alto = più affidabile. Minimo 10 partenze richieste.",
    },
    "top_pilots_by": {"en": "Top 15 Pilots by {ranking}", "es": "Top 15 pilotos por {ranking}", "it": "Top 15 Piloti per {ranking}"},
    "leaderboards": {"en": "Leaderboards", "es": "Tablas de líderes", "it": "Classifiche"},
    "lb_championships": {"en": "**👑 Championships Won**", "es": "**👑 Campeonatos Ganados**", "it": "**👑 Campionati Vinti**"},
    "lb_championships_caption": {"en": "Seasons finished as points leader.", "es": "Temporadas terminadas como líder de puntos.", "it": "Stagioni concluse come leader punti."},
    "lb_race_wins": {"en": "**🏆 Most Race Wins**", "es": "**🏆 Más Victorias en Carrera**", "it": "**🏆 Più Vittorie in Gara**"},
    "lb_race_wins_caption": {"en": "Total Sunday race victories.", "es": "Victorias totales en carreras del domingo.", "it": "Vittorie totali nelle gare della domenica."},
    "lb_sprint_wins": {"en": "**⚡ Most Sprint Wins**", "es": "**⚡ Más Victorias en Sprint**", "it": "**⚡ Più Vittorie Sprint**"},
    "lb_sprint_wins_caption": {"en": "Saturday sprint race victories (from 2023).", "es": "Victorias en sprint del sábado (desde 2023).", "it": "Vittorie sprint del sabato (dal 2023)."},
    "lb_poles": {"en": "**🎯 Most Pole Positions**", "es": "**🎯 Más Pole Positions**", "it": "**🎯 Più Pole Position**"},
    "lb_poles_caption": {"en": "Fastest in Q2 qualifying = front of the grid.", "es": "Más rápido en Q2 = frente de la parrilla.", "it": "Più veloce in Q2 = prima fila della griglia."},
    "lb_podiums": {"en": "**🥇 Most Race Podiums**", "es": "**🥇 Más Podios en Carrera**", "it": "**🥇 Più Podi in Gara**"},
    "lb_podiums_caption": {"en": "Top 3 finishes in main races.", "es": "Top 3 en carreras principales.", "it": "Top 3 nelle gare principali."},
    "lb_efficiency": {"en": "**💯 Best Points Efficiency**", "es": "**💯 Mejor Eficiencia de Puntos**", "it": "**💯 Migliore Efficienza Punti**"},
    "lb_efficiency_caption": {"en": "Actual points ÷ max possible points. Min 10 starts.", "es": "Puntos reales ÷ puntos máximos posibles. Mín. 10 salidas.", "it": "Punti effettivi ÷ punti massimi possibili. Min 10 partenze."},
    "lb_finish_rate": {"en": "**🔧 Best Finish Rate**", "es": "**🔧 Mejor Tasa de Finalización**", "it": "**🔧 Miglior Tasso Completamento**"},
    "lb_finish_rate_caption": {"en": "% of races finished (not DNF/DNS). Min 10 starts.", "es": "% de carreras finalizadas (sin DNF/DNS). Mín. 10 salidas.", "it": "% di gare concluse (non DNF/DNS). Min 10 partenze."},
    "complete_pilot_stats": {"en": "Complete Pilot Statistics", "es": "Estadísticas completas de pilotos", "it": "Statistiche Complete Piloti"},

    # --- Pilot Profile ---
    "pilot_profile_header": {"en": "👤 Pilot Profile", "es": "👤 Perfil del piloto", "it": "👤 Profilo Pilota"},
    "race_starts": {"en": "Race Starts", "es": "Salidas de carrera", "it": "Partenze Gara"},
    "race_wins_label": {"en": "Race Wins", "es": "Victorias en carrera", "it": "Vittorie in Gara"},
    "sprint_starts": {"en": "Sprint Starts", "es": "Salidas de Sprint", "it": "Partenze Sprint"},
    "sprint_wins_label": {"en": "Sprint Wins", "es": "Victorias en Sprint", "it": "Vittorie Sprint"},
    "points_pct": {"en": "Points %", "es": "Puntos %", "it": "Punti %"},
    "profile_seasons_teams": {
        "en": "Seasons: {seasons} · Teams: {teams} · Constructors: {constructors}",
        "es": "Temporadas: {seasons} · equipos: {teams} · constructores: {constructors}",
        "it": "Stagioni: {seasons} · Team: {teams} · Costruttori: {constructors}",
    },
    "race_finishing_positions": {"en": "Race Finishing Positions", "es": "Posiciones de llegada en carrera", "it": "Posizioni di Arrivo in Gara"},
    "race_results_title": {"en": "{pilot} — Race Results", "es": "{pilot} — Resultados de carrera", "it": "{pilot} — Risultati Gara"},
    "points_per_season": {"en": "Points per Season", "es": "Puntos por temporada", "it": "Punti per Stagione"},
    "season_points_title": {"en": "{pilot} — Season Points", "es": "{pilot} — Puntos por temporada", "it": "{pilot} — Punti per Stagione"},
    "season_statistics": {"en": "Season Statistics", "es": "Estadísticas por temporada", "it": "Statistiche per Stagione"},
    "best_lap_evolution": {"en": "Best Race Lap Time Evolution", "es": "Evolución del mejor tiempo de vuelta en carrera", "it": "Evoluzione Miglior Tempo sul Giro in Gara"},
    "race_best_laps_title": {"en": "{pilot} — Race Best Laps", "es": "{pilot} — Mejores vueltas en carrera", "it": "{pilot} — Migliori Giri in Gara"},
    "seconds_label": {"en": "Seconds", "es": "Segundos", "it": "Secondi"},
    "top_speed_trend": {"en": "Top Speed Trend", "es": "Tendencia de velocidad máxima", "it": "Tendenza Velocità Massima"},
    "race_top_speeds_title": {"en": "{pilot} — Race Top Speeds", "es": "{pilot} — Velocidades máximas en carrera", "it": "{pilot} — Velocità Massime in Gara"},
    "head_to_head": {"en": "Head-to-Head Comparison", "es": "Comparación directa", "it": "Confronto Diretto"},
    "compare_with": {"en": "Compare with", "es": "Comparar con", "it": "Confronta con"},
    "ties": {"en": "Ties", "es": "Empates", "it": "Pareggi"},
    "pilot_vs_rival_title": {"en": "{pilot} vs {rival}", "es": "{pilot} vs {rival}", "it": "{pilot} vs {rival}"},

    # --- Cross-Year ---
    "cross_year_header": {"en": "📈 Cross-Year Evolution", "es": "📈 Evolución multi-Temporada", "it": "📈 Evoluzione Multi-Stagione"},
    "cross_year_caption": {"en": "How has MotoGP evolved across seasons? All charts show trends over the loaded years.", "es": "¿Cómo ha evolucionado MotoGP a lo largo de las temporadas? Todos los gráficos muestran tendencias sobre los años cargados.", "it": "Come si è evoluta la MotoGP nelle stagioni? Tutti i grafici mostrano tendenze sugli anni caricati."},
    "chart_label": {"en": "Chart", "es": "Gráfico", "it": "Grafico"},
    "cross_bar_chart_race": {"en": "Animated Bar Chart Race", "es": "Carrera de barras animada", "it": "Gara di barre animata"},
    "bar_chart_race_title": {"en": "🎬 Animated Bar Chart Race", "es": "🎬 Carrera de barras animada", "it": "🎬 Gara di barre animata"},
    "bar_chart_race_caption": {
        "en": "Watch how cumulative wins or points have evolved over the years. Press ▶ to play the animation.",
        "es": "Observa cómo las victorias o puntos acumulados han evolucionado a lo largo de los años. Pulsa ▶ para reproducir la animación.",
        "it": "Guarda come le vittorie o i punti cumulativi si sono evoluti negli anni. Premi ▶ per avviare l'animazione.",
    },
    "metric": {"en": "Metric", "es": "Métrica", "it": "Metrica"},
    "constructor_wins": {"en": "Constructor wins", "es": "Victorias por constructor", "it": "Vittorie per costruttore"},
    "constructor_points": {"en": "Constructor points", "es": "Puntos por constructor", "it": "Punti per costruttore"},
    "rider_wins": {"en": "Rider wins", "es": "Victorias por piloto", "it": "Vittorie per pilota"},
    "rider_points": {"en": "Rider points", "es": "Puntos por piloto", "it": "Punti per pilota"},
    "cumulative_total": {"en": "Cumulative total", "es": "Total acumulado", "it": "Totale cumulativo"},
    "gps_per_frame": {"en": "GPs per animation step", "es": "GPs por paso de animación", "it": "GP per passo animazione"},
    "gps_per_frame_help": {
        "en": "1 = every GP (smoothest, slowest). 20 = every 20 GPs (fastest). Default 5.",
        "es": "1 = cada GP (más suave, más lento). 20 = cada 20 GPs (más rápido). Por defecto 5.",
        "it": "1 = ogni GP (più fluido, più lento). 20 = ogni 20 GP (più veloce). Default 5.",
    },
    "cross_bump_chart": {"en": "Championship Bump Chart", "es": "Bump chart del campeonato", "it": "Bump Chart Campionato"},
    "cross_championship_concentration": {"en": "Championship Concentration", "es": "Concentración del campeonato", "it": "Concentrazione Campionato"},
    "cross_top_riders": {"en": "Top Riders Evolution", "es": "Evolución de los mejores pilotos", "it": "Evoluzione Migliori Piloti"},
    "cross_team_evolution": {"en": "Team Evolution", "es": "Evolución de equipos", "it": "Evoluzione Team"},
    "cross_constructor_evolution": {"en": "Constructor Evolution", "es": "Evolución de constructores", "it": "Evoluzione Costruttori"},
    "cross_rider_career": {"en": "Rider Career Tracker", "es": "Trayectoria del piloto", "it": "Carriera del Pilota"},
    "cross_dnf_safety": {"en": "DNF & Safety Trends", "es": "Tendencias de DNF y seguridad", "it": "Tendenze DNF e Sicurezza"},
    "cross_pole_stats": {"en": "Pole Position Stats", "es": "Estadísticas de Pole position", "it": "Statistiche Pole Position"},
    "cross_qualifying_race": {"en": "Qualifying vs Race", "es": "Clasificación vs carrera", "it": "Qualifica vs Gara"},
    "cross_race_competitiveness": {"en": "Race Competitiveness", "es": "Competitividad de las carreras", "it": "Competitività delle Gare"},
    "cross_season_dominance": {"en": "Season Dominance Index", "es": "Índice de dominancia por temporada", "it": "Indice Dominanza Stagionale"},
    "cross_nationality_trends": {"en": "Nationality Trends", "es": "Tendencias de nacionalidad", "it": "Tendenze Nazionalità"},
    "cross_circuit_pace": {"en": "Circuit Pace Evolution", "es": "Evolución del ritmo en circuito", "it": "Evoluzione Ritmo Circuito"},

    # --- Cross-Year subtitles ---
    "bump_chart_subheader": {"en": "Championship Bump Chart", "es": "Bump chart del campeonato", "it": "Bump Chart Campionato"},
    "bump_chart_caption": {
        "en": "A bump chart shows how championship positions shift after each Grand Prix. Lines crossing = overtakes in the standings. Select a season to see the full narrative.",
        "es": "Un bump chart muestra cómo cambian las posiciones del campeonato tras cada Gran Premio. Líneas que se cruzan = adelantamientos en la clasificación. Seleccione una temporada para ver la historia completa.",
        "it": "Un bump chart mostra come le posizioni del campionato cambiano dopo ogni Gran Premio. Linee che si incrociano = sorpassi in classifica. Seleziona una stagione per vedere la narrativa completa.",
    },
    "bump_chart_title": {"en": "{year} Championship — Position After Each Race", "es": "Campeonato {year} — Posición tras cada carrera", "it": "Campionato {year} — Posizione dopo Ogni Gara"},
    "championship_concentration": {"en": "Championship Concentration", "es": "Concentración del campeonato", "it": "Concentrazione Campionato"},
    "championship_concentration_caption": {
        "en": "What percentage of the **maximum possible points** did the champion and top 3 achieve? Max = 25 pts per race + 12 pts per sprint for every event entered.",
        "es": "¿Qué porcentaje de los **puntos máximos posibles** alcanzaron el campeón y el top 3? Máx = 25 pts por carrera + 12 pts por sprint por cada evento.",
        "it": "Quale percentuale dei **punti massimi possibili** hanno raggiunto il campione e la top 3? Max = 25 punti per gara + 12 punti per sprint per ogni evento.",
    },
    "top3_avg_efficiency": {"en": "Top 3 avg efficiency %", "es": "Eficiencia media top 3 %", "it": "Efficienza media top 3 %"},
    "champion_efficiency": {"en": "Champion efficiency %", "es": "Eficiencia del campeón %", "it": "Efficienza del campione %"},
    "points_efficiency_title": {"en": "Points Efficiency — % of Maximum Possible Points", "es": "Eficiencia de puntos — % de puntos máximos posibles", "it": "Efficienza Punti — % dei Punti Massimi Possibili"},
    "pct_max_possible_points": {"en": "% of Max Possible Points", "es": "% de puntos máximos posibles", "it": "% dei Punti Massimi Possibili"},

    "top_riders_evolution": {"en": "Top Riders — Season-by-Season Stats", "es": "Mejores pilotos — Estadísticas por temporada", "it": "Migliori Piloti — Statistiche per Stagione"},
    "top_riders_evolution_caption": {"en": "Wins, podiums, points, and points % for the most successful riders across all loaded seasons.", "es": "Victorias, podios, puntos y % de puntos de los pilotos más exitosos en todas las temporadas cargadas.", "it": "Vittorie, podi, punti e % punti dei piloti di maggior successo in tutte le stagioni caricate."},
    "race_wins_per_season": {"en": "Race Wins per Season", "es": "Victorias por temporada", "it": "Vittorie per Stagione"},
    "points_efficiency_pct_title": {"en": "Points Efficiency (% of maximum possible)", "es": "Eficiencia de puntos (% del máximo posible)", "it": "Efficienza Punti (% del massimo possibile)"},
    "podiums_per_season": {"en": "Podiums per Season", "es": "Podios por temporada", "it": "Podi per Stagione"},
    "career_totals": {"en": "Career Totals (top riders)", "es": "Totales de carrera (mejores pilotos)", "it": "Totali Carriera (migliori piloti)"},

    "team_evolution": {"en": "Team Evolution Across Seasons", "es": "Evolución de equipos a lo largo de las temporadas", "it": "Evoluzione Team nelle Stagioni"},
    "team_evolution_caption": {
        "en": "How have team fortunes shifted? Teams are grouped by their canonical name (e.g. 'Ducati Factory Team' includes 'Ducati Team' and 'Ducati Lenovo Team').",
        "es": "¿Cómo han cambiado los equipos? Los equipos están agrupados por su nombre canónico (p.ej. 'Ducati factory team' incluye 'ducati team' y 'ducati lenovo team').",
        "it": "Come sono cambiate le sorti dei team? I team sono raggruppati per nome canonico (es. 'Ducati Factory Team' include 'Ducati Team' e 'Ducati Lenovo Team').",
    },
    "team_total_pts_title": {"en": "Team Total Points per Season", "es": "Puntos totales de equipos por temporada", "it": "Punti Totali Team per Stagione"},
    "race_wins_by_team": {"en": "Race Wins by Team per Season", "es": "Victorias por equipo por temporada", "it": "Vittorie per Team per Stagione"},
    "podiums_by_team": {"en": "Podiums by Team per Season", "es": "Podios por equipo por temporada", "it": "Podi per Team per Stagione"},
    "alltime_team_rankings": {"en": "All-Time Team Rankings", "es": "Ranking histórico de equipos", "it": "Classifica Storica Team"},

    "constructor_evolution": {"en": "Constructor Evolution Across Seasons", "es": "Evolución de constructores a lo largo de las temporadas", "it": "Evoluzione Costruttori nelle Stagioni"},
    "constructor_avg_pts_title": {"en": "Constructor Avg Points per Rider", "es": "Media de puntos por piloto del constructor", "it": "Media Punti per Pilota Costruttore"},
    "race_wins_by_constructor": {"en": "Race Wins by Constructor per Season", "es": "Victorias por constructor por temporada", "it": "Vittorie per Costruttore per Stagione"},
    "grid_size_constructor": {"en": "Grid Size per Constructor", "es": "Tamaño de parrilla por constructor", "it": "Dimensione Griglia per Costruttore"},

    "rider_career_tracker": {"en": "Rider Career Tracker", "es": "Trayectoria del piloto", "it": "Carriera del Pilota"},
    "rider_career_caption": {"en": "Compare multiple riders' career metrics side by side across seasons.", "es": "Compare las métricas de carrera de varios pilotos lado a lado a lo largo de las temporadas.", "it": "Confronta le metriche di carriera di più piloti fianco a fianco nelle stagioni."},
    "riders_to_compare": {"en": "Riders to compare", "es": "Pilotos a comparar", "it": "Piloti da confrontare"},
    "metric_label": {"en": "Metric", "es": "Métrica", "it": "Metrica"},
    "metric_per_season": {"en": "{metric} per Season", "es": "{metric} por temporada", "it": "{metric} per Stagione"},
    "cumulative_career_comparison": {"en": "Cumulative Career Comparison", "es": "Comparación acumulada de carrera", "it": "Confronto Cumulativo Carriera"},
    "cumulative_metric_label": {"en": "Cumulative metric", "es": "Métrica acumulada", "it": "Metrica cumulativa"},
    "cumulative_title": {"en": "Cumulative {metric} Over Career", "es": "{metric} acumulados en la carrera", "it": "{metric} Cumulativi nella Carriera"},
    "total_metric": {"en": "Total {metric}", "es": "Total {metric}", "it": "Totale {metric}"},

    "qualifying_vs_race": {"en": "Qualifying vs Race Performance", "es": "Rendimiento clasificación vs carrera", "it": "Prestazioni Qualifica vs Gara"},
    "qualifying_vs_race_caption": {
        "en": "Who gains the most positions from grid to finish? And who loses the most? Negative = gained positions (finished ahead of grid), Positive = lost positions.",
        "es": "¿Quién gana más posiciones de parrilla a meta? ¿Y quién pierde más? Negativo = posiciones ganadas (terminó delante de su posición), positivo = posiciones perdidas.",
        "it": "Chi guadagna più posizioni dalla griglia al traguardo? E chi ne perde di più? Negativo = posizioni guadagnate (finito davanti alla griglia), Positivo = posizioni perse.",
    },
    "best_race_starters_title": {"en": "Best Race Starters — Avg Positions Gained (Grid → Finish)", "es": "Mejores en carrera — Media posiciones ganadas (parrilla → Meta)", "it": "Migliori in Gara — Media Posizioni Guadagnate (Griglia → Arrivo)"},
    "avg_positions_gained": {"en": "Avg Positions Gained", "es": "Media posiciones ganadas", "it": "Media Posizioni Guadagnate"},
    "positions_gained_trend": {"en": "Positions Gained Trend by Season", "es": "Tendencia de posiciones ganadas por temporada", "it": "Tendenza Posizioni Guadagnate per Stagione"},
    "avg_gained_per_season_title": {"en": "Avg Positions Gained per Season (top gainers)", "es": "Media posiciones ganadas por temporada (mejores)", "it": "Media Posizioni Guadagnate per Stagione (migliori)"},
    "avg_gained_label": {"en": "Avg Gained", "es": "Media ganadas", "it": "Media Guadagnate"},
    "grid_vs_finish": {"en": "Grid vs Finish Position (All Races)", "es": "Parrilla vs posición final (todas las carreras)", "it": "Griglia vs Posizione Finale (Tutte le Gare)"},
    "grid_vs_finish_density_title": {"en": "Grid Position vs Race Finish (density)", "es": "Posición de parrilla vs posición final (densidad)", "it": "Posizione Griglia vs Posizione Finale (densità)"},

    "dnf_safety_trends": {"en": "DNF & Safety Trends", "es": "Tendencias de DNF y seguridad", "it": "Tendenze DNF e Sicurezza"},
    "dnf_safety_caption": {"en": "How has race completion evolved? Fewer DNFs may indicate better reliability or safer racing.", "es": "¿Cómo ha evolucionado la finalización de carreras? Menos dNFs pueden indicar mejor fiabilidad o carreras más seguras.", "it": "Come si è evoluto il completamento delle gare? Meno DNF possono indicare migliore affidabilità o gare più sicure."},
    "dnf_rate_title": {"en": "Race DNF Rate per Season", "es": "Tasa de DNF por temporada", "it": "Tasso DNF per Stagione"},
    "dnf_rate_yaxis": {"en": "% of race starters who DNF", "es": "% de los que salieron que no terminaron", "it": "% dei partenti che non hanno finito"},
    "avg_dnf_per_race_title": {"en": "Average DNFs per Race", "es": "DNFs medios por carrera", "it": "DNF Medi per Gara"},
    "avg_dnf_per_race_label": {"en": "Avg DNFs/Race", "es": "Media dNFs/Carrera", "it": "Media DNF/Gara"},
    "race_outcomes_per_season": {"en": "Race Outcomes per Season", "es": "Resultados de carreras por temporada", "it": "Risultati Gare per Stagione"},

    "pole_position_trends": {"en": "Pole Position Trends", "es": "Tendencias de Pole position", "it": "Tendenze Pole Position"},
    "pole_caption": {"en": "Who dominated qualifying? Pole = P1 in the last qualifying session (Q2).", "es": "¿Quién dominó la clasificación? Pole = P1 en la última sesión de clasificación (Q2).", "it": "Chi ha dominato le qualifiche? Pole = P1 nell'ultima sessione di qualifica (Q2)."},
    "poles_per_season_title": {"en": "Pole Positions per Season (Top Qualifiers)", "es": "Pole Positions por temporada (mejores clasificadores)", "it": "Pole Position per Stagione (Migliori Qualificatori)"},
    "poles_by_constructor_title": {"en": "Pole Positions by Constructor", "es": "Pole Positions por constructor", "it": "Pole Position per Costruttore"},
    "alltime_poles": {"en": "All-Time Pole Positions", "es": "Pole Positions históricas", "it": "Pole Position Storiche"},

    "race_competitiveness": {"en": "Race Competitiveness", "es": "Competitividad de las carreras", "it": "Competitività delle Gare"},
    "race_competitiveness_caption": {
        "en": "How close are the races? Measured by the average gap between the winner and the 2nd, 3rd, and 5th place finishers, plus how many different winners per season.",
        "es": "¿Qué tan reñidas son las carreras? Medido por la diferencia media entre el ganador y los puestos 2º, 3º y 5º, más cuántos ganadores diferentes por temporada.",
        "it": "Quanto sono combattute le gare? Misurato dal distacco medio tra il vincitore e il 2°, 3° e 5° classificato, più quanti vincitori diversi per stagione.",
    },
    "different_winners_per_season": {"en": "Number of Different Race Winners per Season", "es": "Número de ganadores diferentes por temporada", "it": "Numero di Vincitori Diversi per Stagione"},
    "avg_winner_gap_title": {"en": "Average Winner's Gap — Are Races Getting Closer?", "es": "Distancia media del ganador — ¿Las carreras son más reñidas?", "it": "Distacco Medio del Vincitore — Le Gare Sono Più Combattute?"},
    "avg_gap_s": {"en": "Avg Gap (s)", "es": "Diferencia media (s)", "it": "Distacco Medio (s)"},

    "season_dominance_index": {"en": "Season Dominance Index", "es": "Índice de dominancia por temporada", "it": "Indice Dominanza Stagionale"},
    "season_dominance_caption": {
        "en": "How dominant was the champion each season? Measured by margin over 2nd place, win rate, and percentage of races on the podium.",
        "es": "¿Qué tan dominante fue el campeón en cada temporada? Medido por el margen sobre el 2º, tasa de victorias y porcentaje de carreras en el podio.",
        "it": "Quanto è stato dominante il campione ogni stagione? Misurato dal margine sul 2° classificato, tasso vittorie e percentuale gare sul podio.",
    },
    "champion_margin_title": {"en": "Champion's Points Margin over Runner-up", "es": "Margen de puntos del campeón sobre el subcampeón", "it": "Margine Punti del Campione sul Secondo"},
    "champion_rates_title": {"en": "Champion's Win & Podium Rate per Season", "es": "Tasa de victorias y podios del campeón por temporada", "it": "Tasso Vittorie e Podi del Campione per Stagione"},

    "nationality_trends": {"en": "Nationality Trends", "es": "Tendencias de nacionalidad", "it": "Tendenze Nazionalità"},
    "nationality_trends_caption": {"en": "How has the national makeup of the grid and podium changed over the years?", "es": "¿Cómo ha cambiado la composición nacional de la parrilla y el podio a lo largo de los años?", "it": "Come è cambiata la composizione nazionale della griglia e del podio nel corso degli anni?"},
    "race_pts_by_nationality": {"en": "Race Points by Nationality", "es": "Puntos de carrera por nacionalidad", "it": "Punti Gara per Nazionalità"},
    "race_wins_by_nationality": {"en": "Race Wins by Nationality", "es": "Victorias por nacionalidad", "it": "Vittorie per Nazionalità"},
    "grid_nationality_diversity": {"en": "Grid Nationality Diversity", "es": "Diversidad de nacionalidades en la parrilla", "it": "Diversità Nazionalità in Griglia"},
    "unique_nationalities": {"en": "Unique Nationalities", "es": "Nacionalidades únicas", "it": "Nazionalità Uniche"},

    "circuit_pace_evolution": {"en": "Circuit Pace Evolution", "es": "Evolución del ritmo en circuito", "it": "Evoluzione Ritmo Circuito"},
    "circuit_pace_caption": {"en": "How have race-winning lap times evolved at each circuit across seasons?", "es": "¿Cómo han evolucionado los tiempos de vuelta ganadores en cada circuito a lo largo de las temporadas?", "it": "Come si sono evoluti i tempi sul giro vincenti in ogni circuito nelle stagioni?"},
    "circuits_multiselect": {"en": "Circuits", "es": "Circuitos", "it": "Circuiti"},
    "winner_best_lap_by_year": {"en": "Winner's Best Lap by Year", "es": "Mejor vuelta del ganador por año", "it": "Miglior Giro del Vincitore per Anno"},
    "lap_s": {"en": "Lap (s)", "es": "Vuelta (s)", "it": "Giro (s)"},
}


def get_translator(lang: str = "en"):
    """Return a translation function for the given language."""
    def t(key: str, **kwargs) -> str:
        entry = TRANSLATIONS.get(key)
        if entry is None:
            return key
        text = entry.get(lang, entry.get("en", key))
        if kwargs:
            text = text.format(**kwargs)
        return text
    return t

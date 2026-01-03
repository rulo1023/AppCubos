import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pycountry



# --- CACHÉ GLOBAL ---
COMP_CACHE = {}
session = requests.Session()
# Adapter para reintentos automáticos si la red falla brevemente
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('https://', adapter)

def fetch_json(url):
    """Helper to fetch JSON with error handling and User-Agent."""
    try:
        # IMPORTANTE: La WCA bloquea peticiones sin User-Agent
        headers = {
            'User-Agent': 'MyCubingApp/1.0 (streamlit_app_viewer)'
        }
        # Timeout un poco más generoso para la API oficial
        response = session.get(url, headers=headers, timeout=10) 
        
        if response.status_code == 404:
            return None
        # Si nos limitan (429), lanzamos error para saberlo (o podrías esperar y reintentar)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # Descomenta esto para depurar si sigue fallando
        # print(f"Error fetching {url}: {e}")
        return None

def get_comp_data(comp_id):
    """
    Fetches competition data. 
    Checks cache first to avoid network calls.
    """
    if comp_id not in COMP_CACHE:
        url = f'https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/competitions/{comp_id}.json'
        data = fetch_json(url)
        if data:
            COMP_CACHE[comp_id] = data
    return COMP_CACHE.get(comp_id)

def prefetch_competitions(comp_ids):
    """
    Parallel fetching of competition data.
    OPTIMIZATION: Increased workers to 50 for faster I/O bound operations.
    """
    to_fetch = [cid for cid in comp_ids if cid not in COMP_CACHE]
    
    if to_fetch:
        # Aumentamos workers a 50 para aprovechar ancho de banda en I/O
        with ThreadPoolExecutor(max_workers=50) as executor:
            executor.map(get_comp_data, to_fetch)

def format_wca_time(cs, event_code=""):
    if cs == -1: return "DNF"
    if cs == -2: return "DNS"
    if cs is None or cs <= 0: return ""
    
    # Si es FMC, la media se guarda multiplicada por 100
    if event_code == "333fm":
        return f"{cs} moves" if cs < 1000 else f"{cs/100:.2f} moves" 
    
    if event_code == "333mbf":
        # cs es el entero codificado (ej. 790321301)
        missed = cs % 100                              # cubos fallados
        time_seconds = (cs // 100) % 100000            # tiempo total en segundos
        points = 99 - (cs // 10_000_000)               # puntos = solved - missed
        solved = points + missed
        attempted = solved + missed

        minutes = time_seconds // 60
        seconds = time_seconds % 60

        return f"{solved}/{attempted} in {minutes}:{seconds:02d}"


    hundredths = cs % 100
    total_seconds = cs // 100
    seconds = total_seconds % 60
    minutes = total_seconds // 60
    
    if minutes > 0:
        return f"{minutes}:{seconds:02d}.{hundredths:02d}s"
    else:
        return f"{seconds}.{hundredths:02d}s"

def get_comp_wcif_public(comp_id):
    """
    Obtiene los datos PÚBLICOS (incluye registro de personas) desde la web de WCA.
    """
    url = f"https://www.worldcubeassociation.org/api/v0/competitions/{comp_id}/wcif/public"
    return fetch_json(url)

def get_wca_results(wca_id):
    """
    Main function to get results. 
    Optimized to fetch all competition info in parallel before processing.
    """
    url = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/persons/{wca_id}.json"
    data = fetch_json(url)
    if not data or "results" not in data: 
        return pd.DataFrame()

    # 1. Identificar todas las competiciones necesarias
    all_comp_ids = list(data["results"].keys())
    
    # 2. Descarga paralela masiva (OPTIMIZACIÓN CLAVE)
    prefetch_competitions(all_comp_ids)

    rows = []
    # Procesamos en orden inverso (más reciente primero normalmente)
    comp_ids_ordered = all_comp_ids[::-1]

    for comp_id in comp_ids_ordered:
        comp_info = COMP_CACHE.get(comp_id) 
        
        # Extracción segura de datos
        comp_name = comp_info.get("name", comp_id) if comp_info else comp_id
        country_iso2 = comp_info.get("country") if comp_info else "Unknown"
        
        # Fecha: Intentamos parsear aquí para que el DataFrame tenga datetime real
        raw_date = comp_info.get("date", {}).get("from") if comp_info else None
        
        events = data["results"][comp_id]
        for event_id, rounds in events.items():
            for r in reversed(rounds):
                solves = r.get("solves", [])
                rows.append({
                    "Competition": comp_id,
                    "CompName": comp_name,
                    "CompDate": raw_date, # Se convierte a datetime abajo
                    "Country": country_iso2,
                    "Event": event_id,
                    "Round": r.get("round"),
                    "best_cs": r.get("best"),
                    "avg_cs": r.get("average"),
                    "time1": solves[0] if len(solves) > 0 else None,
                    "time2": solves[1] if len(solves) > 1 else None,
                    "time3": solves[2] if len(solves) > 2 else None,
                    "time4": solves[3] if len(solves) > 3 else None,
                    "time5": solves[4] if len(solves) > 4 else None,
                })

    df = pd.DataFrame(rows)
    if df.empty: return df
    
    # Convertir fecha a datetime real para ordenamiento correcto
    df['CompDate'] = pd.to_datetime(df['CompDate'], errors='coerce')

    # PR Logic
    def clean_for_min(val):
        return float('inf') if (val is None or val <= 0) else val

    running_best_single = {}
    running_best_avg = {}
    pr_labels = []

    # Sort by date ensures PR logic matches reality
    # Ordenamos por Fecha y luego por Ronda para consistencia
    df = df.sort_values(by=["CompDate", "Round"], ascending=True)

    for idx, row in df.iterrows():
        e, s, a = row["Event"], clean_for_min(row["best_cs"]), clean_for_min(row["avg_cs"])
        
        is_s_pr = s < running_best_single.get(e, float('inf'))
        is_a_pr = a < running_best_avg.get(e, float('inf'))
        
        if is_s_pr: running_best_single[e] = s
        if is_a_pr: running_best_avg[e] = a
        
        label = None
        if is_s_pr and is_a_pr: label = "sin+avg"
        elif is_s_pr: label = "single"
        elif is_a_pr: label = "average"
        pr_labels.append(label)

    df["pr"] = pr_labels
    
    # Retornamos el DF ordenado cronológicamente inverso (más nuevo arriba) para mostrar en tablas
    return df.sort_values(by="CompDate", ascending=False).reset_index(drop=True)

def flatten(obj, parent_key="", sep="."):
    flat = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            flat.update(flatten(v, new_key, sep))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{parent_key}{sep}{i}"
            flat.update(flatten(v, new_key, sep))
    else:
        flat[parent_key] = obj
    return flat

def get_wcaid_info(wca_id):
    url = f"https://www.worldcubeassociation.org/api/v0/persons/{wca_id}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return flatten(r.json())
    except Exception:
        return {}

def prs_info(wca_id, results_df=None):
    if results_df is None:
        results_df = get_wca_results(wca_id)

    # turn results upside down, as its sorted desc by default

    pr_comps = {}
    pr_rows = results_df[results_df['pr'].notnull()].copy()

    for idx, row in pr_rows.iterrows():
        event = row['Event']
        comp_id = row['Competition']
        comp_name = row['CompName']
        # Convertir a string YYYY-MM-DD para display
        comp_date = row['CompDate'].strftime('%Y-%m-%d') if pd.notnull(row['CompDate']) else "Unknown"
        
        pr_type = row['pr']

        def store_pr(kind):
            val_raw = row['best_cs'] if kind == 'single' else row['avg_cs']
            formatted = format_wca_time(val_raw, event)
            key = f"{event}_{kind[:3]}" 
            pr_comps[key] = (comp_id, comp_name, comp_date, formatted, event, kind)

        if pr_type in ['single', 'sin+avg']: store_pr('single')
        if pr_type in ['average', 'sin+avg']: store_pr('average')
            
    return pr_comps

def number_of_prs(wca_id, results_df=None):
    if results_df is None:
        results_df = get_wca_results(wca_id)
        
    total_prs = results_df['pr'].notnull().sum()
    pr_by_event = results_df[results_df['pr'].notnull()]['Event'].value_counts()
    
    pr_summary = {"total": total_prs}
    for event, count in pr_by_event.items():
        pr_summary[event] = count

    return pr_summary

def generate_map_data(wca_id, results_df=None):
    if results_df is None:
        results_df = get_wca_results(wca_id)
    
    if results_df.empty: return

    competitions = results_df['Competition'].unique()
    
    for competition in competitions:
        comp_data = COMP_CACHE.get(competition)
        
        # Chequeo robusto por si falta data en el JSON
        if not comp_data or 'venue' not in comp_data or comp_data['venue'] is None:
            continue
            
        coords = comp_data['venue'].get('coordinates')
        if not coords:
            continue

        name = comp_data.get('name', competition)
        date_start = comp_data.get('date', {}).get('from', "")
        
        lat = coords.get('latitude')
        lon = coords.get('longitude')
        
        if lat is not None and lon is not None:
            yield {
                'lat': float(lat),
                'lon': float(lon),
                'nombre': name,
                'fecha': f"{date_start}"
            }

def get_flag_emoji(country_code):
    if not country_code or country_code == 'N/A':
        return "🌍"
    
    # Casos especiales de la WCA (Multinacional/Multicontinental)
    if country_code.startswith('X'):
        return "🌍"

    if len(country_code) != 2:
        return "🌍"
        
    try:
        return "".join(chr(ord(c.upper()) + 127397) for c in country_code)
    except ValueError:
        return "🌍"

def get_country_name(code):
    """Devuelve el nombre en inglés del país dado su código ISO2."""
    if not code: return "Unknown"

    # --- EXCEPCIONES WCA, si el codigo empieza por X, poner Multiple Countries
    if code.startswith('X'):
        return "Multiple Countries"
    # -----------------------

    try:
        # Busca el país en la base de datos de pycountry
        country = pycountry.countries.get(alpha_2=code)
        return country.name if country else code
    except:
        return code
    
def get_heatmap_data(results_df):
    """Prepara los datos para el heatmap de actividad anual/mensual."""
    if results_df.empty:
        return pd.DataFrame()
    
    # Agrupar por competición única para no contar rondas individuales
    df_unique_comps = results_df.drop_duplicates(subset=['Competition']).copy()
    
    # Extraer año y mes
    df_unique_comps['Year'] = df_unique_comps['CompDate'].dt.year
    df_unique_comps['Month'] = df_unique_comps['CompDate'].dt.month
    
    # Contar competiciones por mes/año
    heatmap_df = df_unique_comps.groupby(['Year', 'Month']).size().reset_index(name='Count')
    return heatmap_df

def get_wca_neighbours(wca_id, year):
    results_df = get_wca_results(wca_id)
    if results_df.empty:
        return pd.DataFrame()

    # 1. Obtenemos las IDs únicas de las competiciones
    all_comp_ids = results_df['Competition'].unique().tolist()
    
    if year and year != "All":
        year_str = str(year).strip()
        # Filtramos solo las que TERMINAN exactamente en el año seleccionado
        # Esto evita errores si el año aparece en medio por casualidad
        my_comp_ids = [c for c in all_comp_ids if str(c).endswith(year_str)]
    else:
        my_comp_ids = all_comp_ids

    if not my_comp_ids:
        # Si no encuentra nada por el ID, intentamos por la fecha (backup de seguridad)
        if year and year != "All":
            results_year = results_df[results_df['CompDate'].dt.year == int(year)]
            my_comp_ids = results_year['Competition'].unique().tolist()
        
        # Si después del backup sigue vacío, salimos
        if not my_comp_ids:
            return pd.DataFrame()

    def process_comp(comp_id):
        # Endpoint de competidores
        url = f"https://www.worldcubeassociation.org/api/v0/competitions/{comp_id}/competitors"
        data = fetch_json(url)
        
        if isinstance(data, list):
            # Extraemos nombres, saltando tu WCA ID
            return [person['name'] for person in data if person.get('wca_id') != wca_id]
        return []

    all_names = []
    # Paralelismo para velocidad
    with ThreadPoolExecutor(max_workers=5) as executor:
        results_lists = list(executor.map(process_comp, my_comp_ids))
        
    for sublist in results_lists:
        all_names.extend(sublist)

    if not all_names:
        return pd.DataFrame()

    # Contar y limpiar
    df_counts = pd.Series(all_names).value_counts().reset_index()
    df_counts.columns = ['Name', 'Count']
    
    return df_counts.head(50)

def get_scrambles(comp_id):
    """
    Obtiene y estructura los scrambles de una competición.
    Estructura de retorno:
    {
        "333": {
            "1": { "A": [ {scramble_obj}, ... ], "B": [...] },
            "f": { "A": [...] }
        },
        ...
    }
    """
    url = f"https://www.worldcubeassociation.org/api/v0/competitions/{comp_id}/scrambles"
    raw_data = fetch_json(url)
    
    if not raw_data:
        return {}

    structured_data = {}

    for item in raw_data:
        ev_id = item['event_id']
        rnd_id = item['round_type_id']
        grp_id = item['group_id']
        
        # Inicializar estructura anidada si no existe
        if ev_id not in structured_data:
            structured_data[ev_id] = {}
        if rnd_id not in structured_data[ev_id]:
            structured_data[ev_id][rnd_id] = {}
        if grp_id not in structured_data[ev_id][rnd_id]:
            structured_data[ev_id][rnd_id][grp_id] = []
        
        # Limpiamos el objeto para quedarnos solo con lo útil
        scramble_obj = {
            "num": item['scramble_num'],
            "scramble": item['scramble'],
            "is_extra": item['is_extra'],
            "id": item['id']
        }
        structured_data[ev_id][rnd_id][grp_id].append(scramble_obj)

    # Ordenar las listas: Primero los NO extra, luego por número
    for ev in structured_data:
        for rnd in structured_data[ev]:
            for grp in structured_data[ev][rnd]:
                # Ordena por (es_extra, numero). False(0) va antes que True(1)
                structured_data[ev][rnd][grp].sort(key=lambda x: (x['is_extra'], x['num']))

    return structured_data

# rapido para probar la funcion de info
if __name__ == "__main__":
    wcaid = "2016LOPE37"


        



    


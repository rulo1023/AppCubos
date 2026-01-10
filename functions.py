import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
from concurrent.futures import ThreadPoolExecutor
import pycountry
import streamlit as st
import time

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
        response = session.get(url, headers=headers, timeout=20) 
        
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

def fetch_names_from_wcif(comp_id):
    """Plan B: Extrae nombres desde el WCIF público."""
    url = f"https://www.worldcubeassociation.org/api/v0/competitions/{comp_id}/wcif/public"
    try:
        response = session.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # En WCIF los competidores están en la lista 'persons'
            if 'persons' in data:
                return [p['name'] for p in data['persons']]
    except Exception as e:
        print(f"Error fatal en WCIF para {comp_id}: {e}")
    return []

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


def get_names_from_competition(comp_id):
    """Descarga y cachea los nombres de una sola competición."""
    url = f"https://www.worldcubeassociation.org/api/v0/competitions/{comp_id}/competitors"
    # Usamos fetch_json que ya tienes definido en tu archivo
    data = fetch_json(url) 
    if isinstance(data, list):
        return [person['name'] for person in data]
    return []

@st.cache_data(show_spinner=False)
def fetch_names_from_comp(comp_id):
    url = f"https://www.worldcubeassociation.org/api/v0/competitions/{comp_id}/competitors"
    
    # INTENTO 1: Endpoint estándar
    try:
        response = session.get(url, timeout=20)
        if response.status_code == 200:
            names = [p['name'] for p in response.json()]
            if len(names) > 0:
                return names
    except:
        pass

    # INTENTO 2: Si el anterior dio 0 o falló, vamos al WCIF (Plan B)
    print(f"⚠️ {comp_id} devolvió 0. Intentando rescate vía WCIF...")
    time.sleep(4) # Pausa de cortesía
    names_wcif = fetch_names_from_wcif(comp_id)
    
    if len(names_wcif) > 0:
        print(f"✅ Rescate exitoso para {comp_id} usando WCIF ({len(names_wcif)} personas)")
        return names_wcif

    return []

def get_wca_neighbours_old(wca_id, year):
    results_df = get_wca_results(wca_id)
    if results_df.empty:
        return pd.DataFrame()

    comp_ids = results_df['Competition'].unique()

    year = str(year)

    
    if year and year != 'All':
        comp_ids = [cid for cid in comp_ids if cid.endswith(year)]

    print(len(comp_ids))

    competitors = {}

    for comp in comp_ids:
        results = fetch_names_from_comp(comp)
        # add names to competitors dict
        for name in results:
            competitors[name] = competitors.get(name, 0) + 1
        print(f"Processed competition {comp}, total competitors so far: {len(competitors)}")
    # Convertir a DataFrame ordenado (Exactamente como lo tenías)
    df_final = pd.DataFrame(list(competitors.items()), columns=['Name', 'Count'])
    df_final = df_final.sort_values(by='Count', ascending=False).reset_index(drop=True)

    return df_final

pause_lock = threading.Lock()

# Bloqueo global
pause_lock = threading.Lock()

def get_wca_neighbours(wca_id, year='All'):
    results_df = get_wca_results(wca_id)
    if results_df.empty:
        return pd.DataFrame()

    comp_ids = results_df['Competition'].unique()
    year = str(year)
    
    if year and year != 'All':
        comp_ids = [cid for cid in comp_ids if cid.endswith(year)]

    def process_single_comp(comp):
        comp = comp.strip()
        
        # 1. ENTRADA: Todos los hilos deben pasar por aquí. 
        # Si uno está durmiendo (bloqueando el lock), los demás se quedan parados aquí.
        with pause_lock:
            # Una vez que consiguen entrar (porque el bloqueo se liberó), 
            # hacemos la petición normal.
            res = fetch_names_from_comp(comp)
        
        # 2. EVALUACIÓN: Si falla, bloqueamos a todos otra vez para la siesta
        if not res or len(res) == 0:
            with pause_lock:
                # Volvemos a comprobar por si otro hilo ya lo arregló mientras esperábamos
                res = fetch_names_from_comp(comp)
                
                if not res or len(res) == 0:
                    print(f"🛑 0 names in {comp}. RELAXING API (6s sleep)...")
                    time.sleep(6) # Aquí es donde el programa se relaja de verdad
                    
                    print(f"🔄 Triggering WCIF rescue for {comp}...")
                    res = fetch_names_from_wcif(comp)
            
        if res and len(res) > 0:
            print(f"✅ {comp}: {len(res)} names")
        else:
            print(f"❌ {comp}: Final 0 names")
            
        return res if res else []

    all_names = []

    # Bajamos a 3 workers. Con 4 o más, a veces las ráfagas son demasiado rápidas 
    # y el bloqueo no llega a tiempo para frenar la siguiente petición.
    with ThreadPoolExecutor(max_workers=3) as executor:
        list_of_results = list(executor.map(process_single_comp, comp_ids))
    
    for names in list_of_results:
        all_names.extend(names)

    if not all_names:
        return pd.DataFrame()

    competitors = {}
    for name in all_names:
        competitors[name] = competitors.get(name, 0) + 1
        
    df_final = pd.DataFrame(list(competitors.items()), columns=['Name', 'Count'])
    return df_final.sort_values(by='Count', ascending=False).reset_index(drop=True)

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

def get_organized_competitions(name_to_search):
    """
    Busca todas las competiciones donde 'name_to_search' aparece como organizador.
    Descarga en paralelo las páginas de la API para mayor velocidad.
    """
    all_competitions = []

    # Función auxiliar para descargar una página específica
    def fetch_page(i):
        url = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/competitions-page-{i}.json"
        return fetch_json(url)

    # El snippet original iteraba 18 páginas. Ponemos 20 por seguridad.
    # Usamos ThreadPoolExecutor para hacer las peticiones en paralelo.
    pages_to_check = range(1, 21)
    
    results = []
    # Reutilizamos la lógica de threads para velocidad
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_page, pages_to_check))

    for data in results:
        if data and 'items' in data:
            for competition in data['items']:
                # Extraemos los nombres de los organizadores
                organisers_names = [org["name"] for org in competition.get("organisers", [])]
                
                # Verificamos si el nombre está en la lista
                if name_to_search in organisers_names:
                    comp_data = {
                        "Nombre": competition.get("name"),
                        "id": competition.get("id"),
                        "city": competition.get("city"),
                        "country": competition.get("country"),
                        "date_start": competition.get("date", {}).get("from"),
                        "date_end": competition.get("date", {}).get("till"),
                        "no_days": competition.get("date", {}).get("numberOfDays")
                    }
                    all_competitions.append(comp_data)

    df = pd.DataFrame(all_competitions)

    if not df.empty:
        # Añadimos la columna "Numero"
        df.insert(0, "Numero", range(1, len(df) + 1))
        
        # Convertimos AMBAS fechas a datetime
        df['date_start'] = pd.to_datetime(df['date_start'])
        df['date_end'] = pd.to_datetime(df['date_end'])  # <--- AÑADIR ESTA LÍNEA
        
        df['Year'] = df['date_start'].dt.year
        # Ordenamos por fecha descendente
        df = df.sort_values(by='date_start', ascending=False)

    return df

# rapido para probar la funcion de info
if __name__ == "__main__":
    wcaid = "2016LOPE37"
    # get the name of the person
    name = get_wcaid_info(wcaid).get("person.name")

    print(name)



        



    


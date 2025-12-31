import requests
import pandas as pd
from datetime import datetime

# Global cache to avoid re-fetching the same competition data
COMP_CACHE = {}
session = requests.Session()

def fetch_json(url):
    """Helper to fetch JSON with error handling."""
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_comp_data(comp_id):
    """Fetches competition data once and stores it in memory."""
    if comp_id not in COMP_CACHE:
        url = f'https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/competitions/{comp_id}.json'
        COMP_CACHE[comp_id] = fetch_json(url)
    return COMP_CACHE[comp_id]

def format_wca_time(cs, event_code=""):
    if cs == -1: return "DNF"
    if cs == -2: return "DNS"
    if cs is None or cs <= 0: return ""
    
    # Si es FMC, no dividimos por 100, son movimientos directos
    if event_code == "333fm":
        return f"{cs} moves" if cs < 1000 else f"{cs/100:.2f} moves" # La media de FMC se guarda como centimoves (ej: 3367)

    hundredths = cs % 100
    total_seconds = cs // 100
    seconds = total_seconds % 60
    minutes = total_seconds // 60
    
    if minutes > 0:
        return f"{minutes}:{seconds:02d}.{hundredths:02d}"
    else:
        return f"{seconds}.{hundredths:02d}"

def get_wca_results(wca_id):
    """Fetches user results and hydrates competition info from cache."""
    url = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/persons/{wca_id}.json"
    data = fetch_json(url)
    if not data: return pd.DataFrame()

    rows = []
    # Comp IDs are keys in the results dict
    comp_ids = list(data["results"].keys())[::-1]

    for comp_id in comp_ids:
        comp_info = get_comp_data(comp_id)
        country_iso2 = comp_info.get("country") if comp_info else "Unknown"
        
        events = data["results"][comp_id]
        for event_id, rounds in events.items():
            for r in reversed(rounds):
                solves = r.get("solves", [])
                rows.append({
                    "Competition": comp_id,
                    "CompName": comp_info.get("name") if comp_info else comp_id,
                    "CompDate": comp_info.get("date", {}).get("from") if comp_info else None,
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
    
    # PR Logic
    def clean_for_min(val):
        return float('inf') if (val is None or val <= 0) else val

    running_best_single = {}
    running_best_avg = {}
    pr_labels = []

    # Sort by date to ensure PR logic is chronological
    df = df.sort_values(by="CompDate", ascending=True)

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
    
    # Final cleanup
    time_cols = ["time1", "time2", "time3", "time4", "time5", "best_cs", "avg_cs"]
    for col in time_cols:
        df[f"{col}_formatted"] = df[col].apply(format_wca_time)

    return df.iloc[::-1].reset_index(drop=True)

def prs_info(wca_id):
    """Refactored to use the already fetched data from get_wca_results."""
    results = get_wca_results(wca_id)
    current_info = get_wcaid_info(wca_id) # The WCA API call
    
    # Filter only rows that are PRs
    pr_rows = results[results['pr'].notna()].copy()
    
    pr_comps = {}
    for _, row in pr_rows.iterrows():
        event = row['Event']
        best_val = 0
        
        # Determine which PR type to store
        types = []
        if row['pr'] in ['single', 'sin+avg']: types.append('single')
        if row['pr'] in ['average', 'sin+avg']: types.append('average')
        
        for kind in types:
            path = f"personal_records.{event}.{kind}.best"
            raw_best = current_info.get(path, 0)
            
            # Formatting logic
            best_time = raw_best / 100
            formatted = f"{int(best_time // 60)}:{best_time % 60:05.2f}" if best_time >= 60 else f"{best_time:.2f}"
            
            pr_comps[f"{event}_{kind[:3]}"] = (
                row['Competition'], 
                row['CompName'], 
                row['CompDate'], 
                formatted, 
                event, 
                kind
            )
            
    return pr_comps

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
    """
    Gets and flattens WCA data for a given WCA ID.
    included person information, records, etc
    important parameters inside of the returned dict will be like:
        - person.name
        - person.country.iso2
        - personal_records.333.single.best
        - personal_records.333.average.best
        - personal_records.333.single.world_rank', continental_rank', national_rank
        - medals.gold, medals.silver, medals.bronze
        - competition_count
        - 'records.national', 'records.continental', 'records.world', 'records.total' 
        - 'total_solves'
    
        event codes: 333, 222, 444, 555, 666, 777, 333bf, 333oh, 333ft,
          clock, minx, pyram, skewb, sq1

    :param wca_id: Description
    """
    url = f"https://www.worldcubeassociation.org/api/v0/persons/{wca_id}"
    r = requests.get(url, timeout=15)

    r.raise_for_status()          # <-- will show an error if the request failed
    data = r.json()

    flat = flatten(data)
    return flat

def get_flag_emoji(country_code):
    if not country_code or country_code == 'N/A' or len(country_code) != 2:
        return "🌍"
    
    # El offset correcto para llegar a Regional Indicator Symbol Letter A (U+1F1E6)
    # 'A' es 65 en ASCII. 127462 - 65 = 127397. 
    # Tu lógica era correcta, pero asegúrate de que el input sea limpio.
    
    try:
        return "".join(chr(ord(c.upper()) + 127397) for c in country_code)
    except ValueError:
        return "🌍"
    
def prs_info(wca_id):
    results = get_wca_results(wca_id)
    # calculate in what comp each pr single and average was achieved
    pr_comps = {}
    current_info = get_wcaid_info(wca_id)
    #reverse results because it's from newest to oldest
    results = results.iloc[::-1].reset_index(drop=True)

    for idx, row in results.iterrows():
        if row['pr'] in ['single', 'sin+avg']:
            pr_comps[f"{row['Event']}_single"] = row['Competition']
        if row['pr'] in ['average', 'sin+avg']:
            pr_comps[f"{row['Event']}_avg"] = row['Competition']
    
    for pr in pr_comps:
        comp_id = pr_comps[pr]

        url = f'https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/competitions/{comp_id}.json'
        data = requests.get(url).json()

        date = data["date"]["from"]
        name = data["name"]

        event = pr.split('_')[0]

        kind_wca = 'average' if pr.endswith('avg') else 'single'

        path = f"personal_records.{event}.{kind_wca}.best"
        
        best_time = current_info.get(path, 0) / 100

        # si el tiempo supera 60 segundos, formatearlo adecuadamente
        if best_time >= 60:
            minutes = int(best_time // 60)
            seconds = best_time % 60
            best_time = f"{minutes}:{seconds:05.2f}"
        else:
            best_time = f"{best_time:.2f}"

        pr_comps[pr] = (comp_id, name, date, best_time, event, kind_wca)
    return pr_comps

def oldest_and_newest_pr(wca_id):
    prs = prs_info(wca_id)
    lista_fechas = []
    for evento, info in prs.items():
        # if evento is in 333ft, magic, mmagic, skip
        if evento.startswith('333ft') or evento.startswith('magic') or evento.startswith('mmagic'):
            continue
        fecha_str = info[2]
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
        lista_fechas.append((fecha_obj, evento, info))

    pr_mas_antiguo = min(lista_fechas, key=lambda x: x[0])
    pr_mas_reciente = max(lista_fechas, key=lambda x: x[0])

    pr_mas_antiguo = pr_mas_antiguo[1:]
    pr_mas_reciente = pr_mas_reciente[1:]

    return pr_mas_antiguo, pr_mas_reciente

def number_countries_participated(wca_id):
    results = get_wca_results(wca_id)
    countries = results['Country'].unique()
    # eliminate countries starting with X
    countries = [c for c in countries if not c.startswith('X')]
    return len(countries)

def number_of_prs(wca_id):
    df = get_wca_results(wca_id)
    total_prs = df['pr'].isin(['single', 'average', 'sin+avg']).sum()

    pr_by_event = df[df['pr'].notnull()]['Event'].value_counts()
    # crear un diccionario, {total: total_prs, '333': n_pr_333, ...
    pr_summary = {"total": total_prs}
    for event, count in pr_by_event.items():
        pr_summary[event] = count

    return pr_summary

def generate_map_data(wca_id):
    # Obtenemos los resultados para saber en qué competiciones participó
    results_df = get_wca_results(wca_id)
    if results_df.empty:
        return

    competitions = results_df['Competition'].unique()
    
    for competition in competitions:
        comp_data = get_comp_data(competition)
        
        # Validación de que existan los datos y las coordenadas
        if not comp_data or 'venue' not in comp_data or 'coordinates' not in comp_data['venue']:
            continue
            
        name = comp_data.get('name', competition)
        date_start = comp_data.get('date', {}).get('from', "")
        date_end = comp_data.get('date', {}).get('till', "")
        
        lat = comp_data['venue']['coordinates'].get('latitude')
        lon = comp_data['venue']['coordinates'].get('longitude')
        
        if lat is not None and lon is not None:
            yield {
                'lat': float(lat),
                'lon': float(lon),
                'nombre': name,
                'fecha': f"{date_start} al {date_end}" if date_start != date_end else date_start
            }

if __name__ == "__main__":
    wcaid = "2016LOPE37"
    mapa = list(generate_map_data(wcaid))
    print(mapa)
    









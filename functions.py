# define a dummy function

import requests, pandas as pd, numpy as np


def format_wca_time(cs):
    if cs == -1: return "DNF"
    if cs == -2: return "DNS"
    if cs is None or cs <= 0: return ""
    hundredths = cs % 100
    total_seconds = cs // 100
    seconds = total_seconds % 60
    minutes = total_seconds // 60
    if minutes > 0:
        return f"{minutes}:{seconds:02d}.{hundredths:02d}"
    return f"{seconds}.{hundredths:02d}"


def get_wca_results(wca_id):
    # This function would normally fetch and calculate stats based on the WCA ID
    # Here we return dummy data for demonstration purposes
    # 1. Fetch and Parse
    person_id = wca_id
    url = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/persons/{person_id}.json"
    data = requests.get(url).json()
    rows = []
    # We reverse the keys to process the oldest competitions first
    comp_ids = list(data["results"].keys())[::-1]

    for comp_id in comp_ids:
        events = data["results"][comp_id]
        for event_id, rounds in events.items():
            # Rounds are usually listed Final -> First, so reverse those too
            for r in reversed(rounds):
                solves = r.get("solves", [])
                rows.append({
                    "Competition": comp_id,
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

    # 2. Logic for PRs
    # DNF (-1) and DNS (-2) must be treated as infinity for comparison
    def clean_for_min(val):
        return float('inf') if val <= 0 else val

    # Track current bests per event
    running_best_single = {}
    running_best_avg = {}
    pr_labels = []

    for idx, row in df.iterrows():
        e = row["Event"]
        s = clean_for_min(row["best_cs"])
        a = clean_for_min(row["avg_cs"])
        
        is_s_pr = s <= running_best_single.get(e, float('inf')) and s != float('inf')
        is_a_pr = a <= running_best_avg.get(e, float('inf')) and a != float('inf')
        
        # Update running bests
        if is_s_pr: running_best_single[e] = s
        if is_a_pr: running_best_avg[e] = a
        
        # Assign labels
        if is_s_pr and is_a_pr: pr_labels.append("sin+avg")
        elif is_s_pr: pr_labels.append("single")
        elif is_a_pr: pr_labels.append("average")
        else: pr_labels.append(None)

    df["pr"] = pr_labels

    # 3. Final Formatting
    time_cols = ["time1", "time2", "time3", "time4", "time5", "best_cs", "avg_cs"]
    for col in time_cols:
        df[col] = df[col].apply(format_wca_time)

    # Rename columns for final output
    df = df.rename(columns={"best_cs": "Best", "avg_cs": "Average"})

    # Reverse back to show newest results at the top
    df = df.iloc[::-1].reset_index(drop=True)

    return(df)


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
    

if __name__ == "__main__":
    prs = get_wcaid_info("2016LOPE37")
    print(prs.keys())






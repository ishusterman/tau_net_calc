import os
import csv
import math
from collections import defaultdict

class roundtrip_analyzer:
    def __init__(self,
                 report_path: str = None,
                 duration_max: int = 3600 * 3,
                 alias="",
                 field_star="Origin_ID",
                 field_hash="Destination_ID",
                 service_area: bool = False):
        self.report_path = report_path
        self.duration_max = duration_max
        self.limit = (2 / 3) * duration_max
        self.alias = alias
        self.field_star = field_star
        self.field_hash = field_hash
        self.service_area = service_area

        self.path_stats = os.path.normpath(os.path.join(self.report_path, f"{self.alias}_round_trip_stats.csv"))
        self.path_bins = os.path.normpath(os.path.join(self.report_path, f"{self.alias}_round_trip_bins.csv"))

        self.states = {}
        self.first_origin = None

    def _init_empty_state(self):
        return {
            "to": {"count": 0, "sum": 0, "sum_sq": 0, "values": []}, # Добавили список values
            "from": {"count": 0, "sum": 0, "sum_sq": 0, "values": []}, # Добавили список values
            "round": {"count": 0, "sum": 0, "sum_sq": 0}
        }
    
    def get_data_for_analyzer_from_to(self, dict_data):

        return {k: v for k, v in dict_data.items() if v <= self.limit}

    def _add_to_state(self, state, val, direction="to"):
        other = "from" if direction == "to" else "to"
        c_alt, s_alt, sq_alt = state[other]["count"], state[other]["sum"], state[other]["sum_sq"]
        
        if c_alt > 0:
            state["round"]["count"] += c_alt
            state["round"]["sum"] += val * c_alt + s_alt
            state["round"]["sum_sq"] += c_alt * val**2 + 2 * val * s_alt + sq_alt

        state[direction]["count"] += 1
        state[direction]["sum"] += val
        state[direction]["sum_sq"] += val**2
        state[direction]["values"].append(val) # Сохраняем конкретное значение

    def _get_key(self, pair):
        o, d = pair
        if self.service_area:
            if self.first_origin is None: self.first_origin = o
            return d
        return (o, d)

    def add_to_data(self, to_data):
        for pair, duration in to_data.items():
            if duration > self.limit: continue
            key = self._get_key(pair)
            if key not in self.states: self.states[key] = self._init_empty_state()
            self._add_to_state(self.states[key], duration, "to")

    def add_from_data(self, from_data):
        for pair, duration in from_data.items():
            if duration > self.limit: continue
            key = self._get_key(pair)
            if key not in self.states: self.states[key] = self._init_empty_state()
            self._add_to_state(self.states[key], duration, "from")

    def finalize_stats(self, state):
        n = state["round"]["count"]
        if n == 0: return 0, 0, 0
        mean = state["round"]["sum"] / n
        var = (state["round"]["sum_sq"] / n) - mean**2
        std = math.sqrt(max(0, var))
        return round(mean, 2), round(std, 2), n

    def run_finalize_all(self):
        rows = []
        final_results = {}
        
        max_to_len = 0
        max_from_len = 0

        # Собираем данные и находим максимумы для заголовков
        for key, st in self.states.items():
            c_to, c_from = st["to"]["count"], st["from"]["count"]
            if c_to == 0 or c_from == 0: continue
            
            mean_to = st["to"]["sum"] / c_to
            mean_from = st["from"]["sum"] / c_from
            if mean_to + mean_from > self.duration_max: continue

            mean, std, count = self.finalize_stats(st)
            if count == 0: continue

            max_to_len = max(max_to_len, c_to)
            max_from_len = max(max_from_len, c_from)

            o_id = self.first_origin if self.service_area else key[0]
            d_id = key if self.service_area else key[1]

            rows.append({
                "o_id": o_id,
                "d_id": d_id,
                "count": count,
                "std": std,
                "c_to": c_to,
                "c_from": c_from,
                "mean": mean,
                "to_vals": st["to"]["values"],
                "from_vals": st["from"]["values"]
            })
            final_results[(o_id, d_id)] = {"mean": mean}

        if self.service_area:
            # Формируем заголовок с новым порядком: 
            # ID -> Временные ряды -> Статистика в конце
            header = [self.field_star, self.field_hash]
            header += [f"TO_{i+1}" for i in range(max_to_len)]
            header += [f"FROM_{i+1}" for i in range(max_from_len)]
            header += ["Count", "Count_to", "Count_from", "Duration_std", "Duration_ave"] # Новые последние столбцы

            with open(self.path_stats, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                
                for r in rows:
                    # Подготовка пустых ячеек для выравнивания столбцов времени
                    to_part = r["to_vals"] + [""] * (max_to_len - len(r["to_vals"]))
                    from_part = r["from_vals"] + [""] * (max_from_len - len(r["from_vals"]))
                    
                    # Сборка строки согласно новому порядку заголовков
                    row_data = [r["o_id"], r["d_id"]] + to_part + from_part + [
                        r["count"],      # Общий Count (round-trip)
                        r["c_to"],       # Count_to
                        r["c_from"],     # Count_from
                        r["std"],        # Std
                        r["mean"]        # Mean
                    ]
                    writer.writerow(row_data)
        else:
            self._save_bins(final_results)

        return self.path_stats if self.service_area else self.path_bins
    
    def _save_bins(self, final_results):
        bin_counts = defaultdict(lambda: defaultdict(int))
        step = 600 
        max_bin_code = self.duration_max // step

        for (o_id, d_id), data in final_results.items():
            bin_code = int(data["mean"] // step)
            if bin_code >= max_bin_code: 
                bin_code = max_bin_code - 1
            bin_counts[o_id][bin_code] += 1

        all_bins = sorted({b for bins in bin_counts.values() for b in bins.keys()})
                
        def get_header(b):
            minutes = (b + 1) * (step // 60)
            max_minutes = self.duration_max // 60
            return f"{min(minutes, max_minutes)}m"

        with open(self.path_bins, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Заменяем [f"bin_{b}" for b in all_bins] на нормальные имена
            writer.writerow([self.field_star] + [get_header(b) for b in all_bins])
            
            for o_id, bins in bin_counts.items():
                row, cumulative = [o_id], 0
                for b in all_bins:
                    cumulative += bins.get(b, 0)
                    row.append(cumulative)
                writer.writerow(row)
        
        return
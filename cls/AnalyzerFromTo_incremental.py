import math
from collections import defaultdict
import pandas as pd

class roundtrip_analyzer:
    def __init__(self,
                 
                 duration_max: int = 3600 * 3,        
                 field_star="Origin_aid",
                 field_hash="Destination_aid",
                 service_area: bool = False,
                 dict_numpoints: dict = None,
                 bin = 600):
        
        self.duration_max = duration_max
        #self.limit = (2 / 3) * duration_max        
        #self.limit = duration_max        
        self.field_star = field_star
        self.field_hash = field_hash
        self.service_area = service_area
        self.dict_numpoints = dict_numpoints if dict_numpoints else {}
        self.bin = bin

        self.states = {}        
        # РАЗДЕЛЯЕМ метки времени
        self.all_to_labels = set()
        self.all_from_labels = set()        

    def get_data_for_analyzer_from_to(self, dict_data):        
        return {k: v for k, v in dict_data.items()}    

    def _init_empty_state(self):
        return {
            "to": {"count": 0, "sum": 0, "sum_sq": 0, "values": []}, 
            "from": {"count": 0, "sum": 0, "sum_sq": 0, "values": []},
            "round": {"count": 0, "sum": 0, "sum_sq": 0}
        }

    def _add_to_state(self, state, val, direction, time_label):
        other = "from" if direction == "to" else "to"
        c_alt, s_alt, sq_alt = state[other]["count"], state[other]["sum"], state[other]["sum_sq"]
        
        if c_alt > 0:
            state["round"]["count"] += c_alt
            state["round"]["sum"] += val * c_alt + s_alt
            state["round"]["sum_sq"] += c_alt * val**2 + 2 * val * s_alt + sq_alt

        state[direction]["count"] += 1
        state[direction]["sum"] += val
        state[direction]["sum_sq"] += val**2
        # Сохраняем парой: (метка, значение)
        state[direction]["values"].append((time_label, val))
        
        if direction == "to":
            self.all_to_labels.add(time_label)
        else:
            self.all_from_labels.add(time_label)

    def add_to_data(self, to_data, time_label: str):
        for pair, duration in to_data.items():
            #if duration > self.limit: continue
            o, d = pair
            key = (o, d)            
            if key not in self.states: self.states[key] = self._init_empty_state()
            self._add_to_state(self.states[key], duration, "to", time_label)

    def add_from_data(self, from_data, time_label: str):
        for pair, duration in from_data.items():
            #if duration > self.limit: continue
            o, d = pair
            key = (o, d)            
            if key not in self.states: self.states[key] = self._init_empty_state()
            self._add_to_state(self.states[key], duration, "from", time_label)

    def finalize_stats(self, state):
        n = state["round"]["count"]
        if n == 0: return 0, 0, 0
        mean = state["round"]["sum"] / n
        var = (state["round"]["sum_sq"] / n) - mean**2
        std = math.sqrt(max(0, var))
        return round(mean, 2), round(std, 2), n

    def run_finalize_all(self):
        # 1. Подготовка метаданных
        sorted_to_labels = sorted(list(self.all_to_labels))
        sorted_from_labels = sorted(list(self.all_from_labels))
        
        target_to = self.all_to_labels
        target_from = self.all_from_labels

        rows_standard = []
        rows_strict = []
        results_standard = {}
        results_strict = {}

        for key, st in self.states.items():
            if st["to"]["count"] == 0 or st["from"]["count"] == 0:
                continue

            mean, std, count = self.finalize_stats(st)
            if count == 0:
                continue

            to_map = {lbl: val for lbl, val in st["to"]["values"]}
            from_map = {lbl: val for lbl, val in st["from"]["values"]}

            
            o_id, d_id = key  # теперь key всегда (o, d)
            
            if mean > self.duration_max:
                continue
            
            row_entry = {
                "o_id": o_id, "d_id": d_id, "mean": mean, "std": std, "count": count,
                "c_to": st["to"]["count"], "c_from": st["from"]["count"],
                "to_map": to_map, "from_map": from_map
            }

            rows_standard.append(row_entry)
            results_standard[(o_id, d_id)] = {"mean": mean}

            if target_to.issubset(to_map.keys()) and target_from.issubset(from_map.keys()):
                rows_strict.append(row_entry)
                results_strict[(o_id, d_id)] = {"mean": mean}
        
        def make_pivot_from_rows(rows, col_star, col_hash, value_field="mean", prefix="Duration_"):       
        
            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame([
                {
                    col_star: r["o_id"],   # или r["o_id"], зависит от твоей логики
                    col_hash: r["d_id"],   # смотри ниже пояснение
                    value_field: r[value_field]
                }
                for r in rows
            ])

            # pivot
            pivot = df.pivot(index=col_hash, columns=col_star, values=value_field).reset_index()

            pivot.rename(columns={pivot.columns[0]: col_star}, inplace=True)

            # добавляем префикс Duration_
            new_cols = [pivot.columns[0]] + [f"{prefix}{c}" for c in pivot.columns[1:]]
            pivot.columns = new_cols

            return pivot
        def select_best_origin_per_destination(rows):
            """
            Для каждого d_id выбираем строку с минимальной комбинацией:
            min(TO) + min(FROM)
            """
            best_by_dest = {}

            for r in rows:
                d_id = r["d_id"]

                # фильтруем только числовые значения
                to_vals = [v for v in r["to_map"].values() if isinstance(v, (int, float))]
                from_vals = [v for v in r["from_map"].values() if isinstance(v, (int, float))]

                if not to_vals or not from_vals:
                    continue

                min_to = min(to_vals)
                min_from = min(from_vals)

                metric = min_to + min_from
                r["_metric"] = metric

                cur_best = best_by_dest.get(d_id)

                if cur_best is None or metric < cur_best["_metric"]:
                    best_by_dest[d_id] = r

            return list(best_by_dest.values())

        # Внутренняя функция для создания "плоского" списка словарей для DataFrame
        def prepare_df_rows(rows):
            flattened = []
            for r in rows:
                # Базовые поля (переименовываем ключи под header)
                d = {
                    self.field_star: r["d_id"],  
                    self.field_hash: r["o_id"], 
                    #self.field_star: r["o_id"],
                    #self.field_hash: r["d_id"],
                    "Duration_ave": r["mean"],
                    "Duration_std": r["std"],
                    "Count": r["count"],
                    "Count_to": r["c_to"],
                    "Count_from": r["c_from"]
                }
                # Распаковываем динамические колонки меток
                for lbl in sorted_to_labels:
                    d[f"TO_{lbl}"] = r["to_map"].get(lbl, "")
                for lbl in sorted_from_labels:
                    d[f"FROM_{lbl}"] = r["from_map"].get(lbl, "")
                flattened.append(d)
            return flattened

        
        def get_header(rows):
            if not rows: return None
            header = [self.field_star, self.field_hash, "Duration_ave", "Duration_std", "Count", "Count_to", "Count_from"]
            header += [f"TO_{lbl}" for lbl in sorted_to_labels]
            header += [f"FROM_{lbl}" for lbl in sorted_from_labels]            
            
            return header
        
        pivot_standard = make_pivot_from_rows(
                    rows_standard,
                    col_star=self.field_star,
                    col_hash=self.field_hash,
                    value_field="mean",
                    prefix="Duration_mean_"
                )


        if self.service_area:
            # Выбираем для каждого destination тот origin, у которого минимальный roundtrip
            rows_standard_best = select_best_origin_per_destination(rows_standard)
            rows_strict_best = select_best_origin_per_destination(rows_strict)

            header = get_header(rows_standard_best)
            
            df_stats_std = pd.DataFrame(prepare_df_rows(rows_standard_best))
            df_stats_strict = pd.DataFrame(prepare_df_rows(rows_strict_best))
            
            return df_stats_std, df_stats_strict, header, pivot_standard
        else:
            df_rows_std, header = self._save_bins_custom(results_standard)
            df_rows_strict, _ = self._save_bins_custom(results_strict)
            return df_rows_std, df_rows_strict, header, pivot_standard

    def _save_bins_custom(self, final_results):
        """Вспомогательный метод для сохранения бинов"""
        bin_weights = defaultdict(lambda: defaultdict(float))
        step = self.bin 
        max_bin_code = self.duration_max // step
        df_rows_list = []

        for (o_id, d_id), data in final_results.items():
            bin_code = int(data["mean"] // step)
            if bin_code >= max_bin_code: bin_code = max_bin_code - 1
            weight = self.dict_numpoints.get(int(d_id), 1)
            bin_weights[o_id][bin_code] += weight
            

        all_bins = sorted({b for bins in bin_weights.values() for b in bins.keys()})

        # Добавляем последний бин, если он не достигает duration_max
        last_minutes = (all_bins[-1] + 1) * step // 60
        full_minutes = self.duration_max // 60
        if last_minutes < full_minutes:
            all_bins.append(all_bins[-1] + 1)
        
        def get_header(b):
            minutes = (b + 1) * step // 60
            minutes = min(minutes, full_minutes)
            minutes = int(minutes) 
            return f"{minutes}m"

            



        header = [self.field_hash] + [get_header(b) for b in all_bins]
        
        for o_id, bins in bin_weights.items():
                row, cumulative = [o_id], 0
                for b in all_bins:
                    cumulative += bins.get(b, 0)
                    row.append(round(cumulative)) 
                df_rows_list.append(row) # Добавляем готовую строку для DataFrame

        # Создаем DataFrame с правильными заголовками
        df_rows = pd.DataFrame(df_rows_list, columns=header)
        return df_rows, header
    
    

    
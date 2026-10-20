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
                 bin = 600,
                 imbalance: float = 2.0,
                 min_activity_duration: int = 0,
                 check_min_activity_duration: bool = False):
        
        self.duration_max = duration_max
        self.field_star = field_star
        self.field_hash = field_hash
        self.service_area = service_area
        self.dict_numpoints = dict_numpoints if dict_numpoints else {}
        self.bin = bin

        self.imbalance = imbalance
        self.min_activity_duration = min_activity_duration
        self.check_min_activity_duration = check_min_activity_duration

        self.states = {}       
        self.all_to_labels = set()
        self.all_from_labels = set()    

    def _check_imbalance(self, t_a, t_b):
        """Check: T_a <= k * T_b и T_b <= k * T_a"""
        return (t_a <= self.imbalance * t_b) and (t_b <= self.imbalance * t_a)

    def _check_activity_duration(self, to_end, from_start):
        """Проверка: если флаг выключен, проверка пропускается"""
        if not self.check_min_activity_duration:
            return True
        return (from_start - to_end) >= self.min_activity_duration

    def get_data_for_analyzer_from_to(self, dict_data):       
        return {k: v for k, v in dict_data.items()}    

    def _init_empty_state(self):
        return {
            "to": {"count": 0, "sum": 0, "sum_sq": 0, "values": []}, 
            "from": {"count": 0, "sum": 0, "sum_sq": 0, "values": []},
            "round": {"count": 0, "sum": 0, "sum_sq": 0}
        }

    def _add_to_state(self, state, val, start_time, end_time, direction, time_label):
        other = "from" if direction == "to" else "to"

        for alt_item in state[other]["values"]:
            alt_lbl, alt_val, alt_start, alt_end = alt_item
            
            # Определяем временные границы to и from
            if direction == "to":
                to_end = end_time
                from_start = alt_start
            else:
                to_end = alt_end
                from_start = start_time

            # Проверяем паузу активности (с учетом флага) и дисбаланс
            if self._check_activity_duration(to_end, from_start) and self._check_imbalance(val, alt_val):
                round_duration = val + alt_val
                state["round"]["count"] += 1
                state["round"]["sum"] += round_duration
                state["round"]["sum_sq"] += round_duration ** 2

        state[direction]["count"] += 1
        state[direction]["sum"] += val
        state[direction]["sum_sq"] += val**2
        state[direction]["values"].append((time_label, val, start_time, end_time))
        
        if direction == "to":
            self.all_to_labels.add(time_label)
        else:
            self.all_from_labels.add(time_label)

    def add_to_data(self, to_data, time_label: str):
        for pair, entry in to_data.items():
            start_time, end_time, duration = entry
            key = pair            

            if key not in self.states: 
                self.states[key] = self._init_empty_state()
            self._add_to_state(self.states[key], duration, start_time, end_time, "to", time_label)

    def add_from_data(self, from_data, time_label: str):
        for pair, entry in from_data.items():
            start_time, end_time, duration = entry
            key = pair            
            if key not in self.states: 
                self.states[key] = self._init_empty_state()
            self._add_to_state(self.states[key], duration, start_time, end_time, "from", time_label)

    def finalize_stats(self, state):
        n = state["round"]["count"]
        if n == 0: return 0, 0, 0
        mean = state["round"]["sum"] / n
        var = (state["round"]["sum_sq"] / n) - mean**2
        std = math.sqrt(max(0, var))
        return round(mean, 2), round(std, 2), n

    def run_finalize_all(self):
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

            to_map = {item[0]: item[1] for item in st["to"]["values"]}
            from_map = {item[0]: item[1] for item in st["from"]["values"]}

            o_id, d_id = key
                        
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
                    col_star: r["o_id"],
                    col_hash: r["d_id"],
                    value_field: r[value_field]
                }
                for r in rows
            ])

            pivot = df.pivot(index=col_hash, columns=col_star, values=value_field).reset_index()
            pivot.rename(columns={pivot.columns[0]: col_star}, inplace=True)
            new_cols = [pivot.columns[0]] + [f"{prefix}{c}" for c in pivot.columns[1:]]
            pivot.columns = new_cols

            duration_cols = pivot.columns[1:]
            pivot["No_reachable"] = pivot[duration_cols].notna().sum(axis=1)
            pivot["Duration_mean"] = pivot[duration_cols].mean(axis=1)

            first_col = pivot.columns[0]
            ordered_cols = [first_col, "No_reachable", "Duration_mean"] + duration_cols.tolist()
            pivot = pivot[ordered_cols]

            max_cols = 1000 + 3
            if pivot.shape[1] > max_cols:
                keep_cols = pivot.columns[:max_cols]
                pivot = pivot[keep_cols]

            return pivot

        def select_best_origin_per_destination(rows):
            best_by_dest = {}
            for r in rows:
                d_id = r["d_id"]
                to_vals = [v for v in r["to_map"].values() if isinstance(v, (int, float))]
                from_vals = [v for v in r["from_map"].values() if isinstance(v, (int, float))]

                if not to_vals or not from_vals:
                    continue

                metric = min(to_vals) + min(from_vals)
                r["_metric"] = metric

                cur_best = best_by_dest.get(d_id)
                if cur_best is None or metric < cur_best["_metric"]:
                    best_by_dest[d_id] = r

            return list(best_by_dest.values())

        def prepare_df_rows(rows):
            flattened = []
            for r in rows:
                d = {
                    self.field_star: r["d_id"],  
                    self.field_hash: r["o_id"], 
                    "Duration_ave": r["mean"],
                    "Duration_std": r["std"],
                    "Count": r["count"],
                    "Count_to": r["c_to"],
                    "Count_from": r["c_from"]
                }
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
            rows_standard_best = select_best_origin_per_destination(rows_standard)
            header = get_header(rows_standard_best)
            df_stats_std = pd.DataFrame(prepare_df_rows(rows_standard_best))
            df_stats_strict = {}
            return df_stats_std, df_stats_strict, header, pivot_standard
        else:
            df_rows_std, header = self._save_bins_custom(results_standard)
            df_rows_strict = {}
            return df_rows_std, df_rows_strict, header, pivot_standard

    def _save_bins_custom(self, final_results):
        step = self.bin
        max_bin_code = self.duration_max // step

        def compute_bin_weights(weight_dict=None):
            bin_weights = defaultdict(lambda: defaultdict(float))
            for (o_id, d_id), data in final_results.items():
                bin_code = int(data["mean"] // step)
                if bin_code >= max_bin_code:
                    bin_code = max_bin_code - 1

                weight = 1 if weight_dict is None else weight_dict.get(int(d_id), 1)
                bin_weights[o_id][bin_code] += weight
            return bin_weights

        def build_df(bin_weights):
            all_bins = sorted({b for bins in bin_weights.values() for b in bins.keys()})
            last_minutes = (all_bins[-1] + 1) * step // 60
            full_minutes = self.duration_max // 60
            if last_minutes < full_minutes:
                all_bins.append(all_bins[-1] + 1)

            def get_header(b):
                minutes = (b + 1) * step // 60
                minutes = min(minutes, full_minutes)
                return f"{int(minutes)}m"

            header = [self.field_hash] + [get_header(b) for b in all_bins]

            df_rows_list = []
            for o_id, bins in bin_weights.items():
                row, cumulative = [o_id], 0
                for b in all_bins:
                    cumulative += bins.get(b, 0)
                    row.append(round(cumulative))
                df_rows_list.append(row)

            return pd.DataFrame(df_rows_list, columns=header), header

        bin_nbldg = compute_bin_weights(weight_dict=None)
        df_nbldg, header = build_df(bin_nbldg)

        result_all_fields = {"nbldg": df_nbldg}

        for field_name, dict_np in self.dict_numpoints.items():
            bin_w = compute_bin_weights(weight_dict=dict_np)
            df_field, _ = build_df(bin_w)
            result_all_fields[field_name] = df_field

        return result_all_fields, header
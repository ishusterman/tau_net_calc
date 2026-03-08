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
        """
        :param service_area: Если True, используется логика первого класса (ключ - только D).
                             Если False, используется логика второго класса (ключ - пара O, D).
        """
        self.report_path = report_path
        self.duration_max = duration_max
        self.limit = (2 / 3) * duration_max
        self.alias = alias
        self.field_star = field_star
        self.field_hash = field_hash
        self.service_area = service_area

        self.path_stats = os.path.normpath(os.path.join(self.report_path, f"{self.alias}_round_trip_stats.csv"))
        self.path_bins = os.path.normpath(os.path.join(self.report_path, f"{self.alias}_round_trip_bins.csv"))

        # Состояние: ключ -> структура данных статистики
        self.states = {}
        # Хранение первого Origin для режима service_area
        self.first_origin = None

    def get_data_for_analyzer_from_to(self, dict_data):
        return {k: v for k, v in dict_data.items() if v <= self.limit}
    
    # -------------------------------------------------------------------------
    # Вспомогательные методы статистики
    # -------------------------------------------------------------------------
    def _init_empty_state(self):
        return {
            "to": {"count": 0, "sum": 0, "sum_sq": 0},
            "from": {"count": 0, "sum": 0, "sum_sq": 0},
            "round": {"count": 0, "sum": 0, "sum_sq": 0}
        }

    def _add_to_state(self, state, val, direction="to"):
        other = "from" if direction == "to" else "to"
        
        # Обновляем статистику round-trip на основе накопленных данных противоположного направления
        c_alt, s_alt, sq_alt = state[other]["count"], state[other]["sum"], state[other]["sum_sq"]
        
        if c_alt > 0:
            state["round"]["count"] += c_alt
            state["round"]["sum"] += val * c_alt + s_alt
            state["round"]["sum_sq"] += c_alt * val**2 + 2 * val * s_alt + sq_alt

        # Обновляем статистику текущего направления
        state[direction]["count"] += 1
        state[direction]["sum"] += val
        state[direction]["sum_sq"] += val**2

    # -------------------------------------------------------------------------
    # Обработка данных
    # -------------------------------------------------------------------------
    def _get_key(self, pair):
        """Возвращает ключ в зависимости от режима."""
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

    def init_from_data(self, to_data, from_data):
        self.add_to_data(to_data)
        self.add_from_data(from_data)

    # -------------------------------------------------------------------------
    # Финализация и сохранение
    # -------------------------------------------------------------------------
    def finalize_stats(self, state):
        n = state["round"]["count"]
        if n == 0: return 0, 0, 0
        
        mean = state["round"]["sum"] / n
        var = (state["round"]["sum_sq"] / n) - mean**2
        std = math.sqrt(max(0, var)) # Защита от отрицательного var из-за точности float
        return round(mean, 2), round(std, 2), n

    def run_finalize_all(self):
        rows = []
        final_results = {}

        for key, st in self.states.items():
            c_to, c_from = st["to"]["count"], st["from"]["count"]
            if c_to == 0 or c_from == 0: continue

            mean_to = st["to"]["sum"] / c_to
            mean_from = st["from"]["sum"] / c_from

            if mean_to + mean_from > self.duration_max: continue

            mean, std, count = self.finalize_stats(st)
            if count == 0: continue

            # Определяем O и D для записи в CSV
            o_id = self.first_origin if self.service_area else key[0]
            d_id = key if self.service_area else key[1]

            rows.append([o_id, d_id, count, std, c_to, c_from, mean])
            final_results[(o_id, d_id)] = {"mean": mean}

        if self.service_area:
            # Сохранение статистики
            with open(self.path_stats, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([self.field_star, self.field_hash, "Count", "Std", "Count_to", "Count_from", "Mean"])
                writer.writerows(rows)
        else:
            # Сохранение бинов
            self._save_bins(final_results)

        result = self.path_stats if self.service_area else self.path_bins

        return result
    """
    def _save_bins(self, final_results):
        bin_counts = defaultdict(lambda: defaultdict(int))
        max_bin_code = self.duration_max // 600

        for (o_id, d_id), data in final_results.items():
            bin_code = int(data["mean"] // 600)
            if bin_code >= max_bin_code: bin_code = max_bin_code - 1
            bin_counts[o_id][bin_code] += 1

        all_bins = sorted({b for bins in bin_counts.values() for b in bins.keys()})
        
        with open(self.path_bins, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([self.field_star] + [f"bin_{b}" for b in all_bins])
            for o_id, bins in bin_counts.items():
                row, cumulative = [o_id], 0
                for b in all_bins:
                    cumulative += bins.get(b, 0)
                    row.append(cumulative)
                writer.writerow(row)
        
        return 
    """
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
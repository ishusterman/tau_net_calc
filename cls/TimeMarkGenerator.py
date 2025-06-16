import csv
import random
from datetime import timedelta


class TimeMarkGenerator:
    def __init__(self, start_hour, end_hour, marks_per_hour, n_experiments):
        self.start_seconds = start_hour * 3600
        self.end_seconds = end_hour * 3600
        self.marks_per_hour = marks_per_hour
        self.n_experiments = n_experiments
        
    def generate_hourly_ranges(self):
        current = self.start_seconds - (self.start_seconds % 3600)
        while current < self.end_seconds:
            next_hour = min(current + 3600, self.end_seconds)
            yield current, next_hour
            current += 3600

    def generate_time_marks(self, start_sec, end_sec):
        duration = end_sec - start_sec
        marks = sorted(random.uniform(0, duration) for _ in range(self.marks_per_hour))
        return [round(start_sec + s) for s in marks]

    def seconds_to_time_string(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def time_str_to_seconds(self, time_str):
        h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s


    def run(self):
        all_rows = []
        time_set = set()

        for experiment_id in range(1, self.n_experiments + 1):
            for hour_start, hour_end in self.generate_hourly_ranges():
                marks = self.generate_time_marks(hour_start, hour_end)
                for sec in marks:
                    time_str = self.seconds_to_time_string(sec)
                    all_rows.append([experiment_id, sec, time_str])
                    time_set.add(time_str)

        
        # Сортируем по числовому значению времени
        sorted_times = sorted(time_set, key=self.time_str_to_seconds)
        return sorted_times

# === Пример использования ===
if __name__ == '__main__':
    generator = TimeMarkGenerator(
        start_hour=7,
        end_hour=19,
        marks_per_hour=2,
        n_experiments=1)
    
    times = generator.run()
    print(times)


import time
import multiprocessing
import os

def process_data_with_math(data_item):
    """
    Применяет ресурсоемкую математическую операцию к элементу данных.
    Эта функция будет выполняться в дочерних процессах.
    """
    def fib_recursive(n):
        if n <= 1:
            return n
        return fib_recursive(n - 1) + fib_recursive(n - 2)

    fib_number = 35
    fib_recursive(fib_number)
    
    # Этот print() будет отправлен в stdout и перехвачен основным процессом.
    print(f"Data item {data_item} processed.")
    
    return f"Result for {data_item}"

def run_multi_process_task():
    """
    Запускает многопроцессорную задачу.
    """
    print("----------------------------------------")
    print("Starting multiprocessing task...")
    print("----------------------------------------")
    
    start_time = time.time()
    num_processes = multiprocessing.cpu_count()
    print(f"Using {num_processes} processors.")

    with multiprocessing.Pool(processes=num_processes) as pool:
        # pool.map выполняет process_data_with_math для каждого элемента в range(10)
        results = pool.map(process_data_with_math, range(10))

    end_time = time.time()
    
    print("----------------------------------------")
    print(f"Multiprocessing completed: {end_time - start_time:.4f} s")
    print("Results:", results)
    print("----------------------------------------")
    
if __name__ == "__main__":
    # Эта строка необходима для корректной работы multiprocessing в Windows.
    multiprocessing.freeze_support()
    run_multi_process_task()
    print("Press any key to close the window...")
    os.system("pause") # For Windows

import shutil
import os

from src import *

results_dir = 'results'
if os.path.exists(results_dir):
    shutil.rmtree(results_dir)
    os.makedirs(results_dir, exist_ok=True)

if __name__ == "__main__":
    step_1_1()
    step_1_2()
    step_2_1()
    step_2_2()
    step_3_1()
    step_3_2()
    step_4_1()
    step_4_2()
    step_5()
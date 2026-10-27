import kagglehub
import shutil
import os

# Download latest version of the dataset
path = kagglehub.dataset_download("asaniczka/tmdb-movies-dataset-2023-930k-movies")
print("Dataset downloaded to cache:", path)

# The dataset folder contains a CSV file. Let's find it and copy it here.
csv_file = None
for file in os.listdir(path):
    if file.endswith(".csv"):
        csv_file = os.path.join(path, file)
        break

if csv_file:
    dest = os.path.join(os.getcwd(), "movies_dataset_1M.csv")
    shutil.copy(csv_file, dest)
    print("Successfully copied dataset to:", dest)
else:
    print("Could not find a CSV file in the downloaded dataset.")

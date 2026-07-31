import pandas as pd
import logging
import os


# Configure logging
logging.basicConfig(level=logging.INFO)


def load_metrics(file_path):
    """
    Load AWS metrics from a CSV file.
    """

    # Check if file exists
    if not os.path.exists(file_path):
        logging.error("File not found.")
        return None

    try:
        metrics = pd.read_csv(file_path)

        logging.info("Metrics loaded successfully.")

        return metrics

    except Exception as e:
        logging.error(f"Error reading file: {e}")

        return None
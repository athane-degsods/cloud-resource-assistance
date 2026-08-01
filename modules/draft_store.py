import json
import os

# Path to the JSON file
FILE_PATH = os.path.join(os.path.dirname(__file__), "draft_store.json")


def _read_file():
    """
    Read all stored drafts from the JSON file.
    Returns an empty dictionary if the file does not exist
    or contains invalid JSON.
    """

    if not os.path.exists(FILE_PATH):
        return {}

    try:
        with open(FILE_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _write_file(data):
    """
    Write all drafts to the JSON file.
    """

    try:
        with open(FILE_PATH, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
    except OSError:
        print("Error: Unable to write to draft_store.json")


def put(request_id, model_response):
    """
    Save or update a model response using the request ID.
    """

    drafts = _read_file()

    drafts[request_id] = model_response

    _write_file(drafts)


def get(request_id):
    """
    Return the stored model response.

    Returns:
        dict: Stored model response.
        None: If the request ID is not found.
    """

    drafts = _read_file()

    return drafts.get(request_id)


def clear(request_id):
    """
    Remove a stored draft using the request ID.
    """

    drafts = _read_file()

    if request_id in drafts:
        del drafts[request_id]
        _write_file(drafts)


if __name__ == "__main__":

    # Example usage

    sample_response = {
        "status": "success",
        "summary": "Sample response"
    }

    put("request_001", sample_response)

    print("Stored Response:")
    print(get("request_001"))

    clear("request_001")

    print("After Clear:")
    print(get("request_001"))
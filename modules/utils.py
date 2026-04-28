import zipfile
import io

def create_zip(results_dict):
    """
    Takes a dictionary of {filename: bytes}
    Returns a BytesIO zip buffer
    """

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, file in results_dict.items():
            zf.writestr(fname, file)

    zip_buffer.seek(0)
    return zip_buffer

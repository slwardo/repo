import subprocess
import os
import io
import sys
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError

# --- Google Drive API Setup ---
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']  # Read-only access is sufficient

try:
    creds, project_id = default(scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    print("Successfully authenticated using ADC.")
except DefaultCredentialsError as e:
    print(f"Error: Could not obtain default credentials. Ensure you have logged in with gcloud auth application-default login. {e}")
    sys.exit(1)

def download_file_from_drive(file_id):
    """Downloads a file from Google Drive and returns its content."""
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_content = request.execute()
        return io.BytesIO(file_content)
    except Exception as e:
        print(f"Error downloading file {file_id}: {e}")
        return None


def convert_to_pdf(input_file_content, output_path, file_name):
    """Converts a file-like object to PDF using LibreOffice."""
    if os.name == 'nt':  # Windows
        libreoffice_path = r"C:\Program Files\LibreOffice\program\soffice.exe"  # Adjust this path if needed
    elif os.name == 'posix':  # Linux/macOS
        libreoffice_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"  # Or /opt/libreoffice/program/soffice
    else:
        raise OSError("Unsupported operating system")

    # Sanitize file name for temporary file
    sanitized_file_name = "".join(c for c in file_name if c.isalnum() or c in (' ', '.', '_')).rstrip()
    temp_input_path = f"/tmp/{sanitized_file_name}"

    with open(temp_input_path, 'wb') as temp_file:
        temp_file.write(input_file_content.getvalue())

    command = [libreoffice_path, "--headless", "--convert-to", "pdf", temp_input_path, "--outdir", output_path]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error: LibreOffice conversion failed: {e.stderr}")
    except Exception as e:
        print(f"Error during conversion: {e}");
    
    finally:
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)  # Clean up the temporary file

def process_drive_files(input_file_path, output_dir):
    """Reads URLs from input_file, downloads corresponding Drive files, and converts to PDFs."""
    os.makedirs(output_dir, exist_ok=True)  # Create output directory if it doesn't exist
    url = None
    file_name = None  # Initialize file_name here
    mime_type = None  # Initialize mime_type here
    with open(input_file_path, 'r') as f:
        for url in f:
            url = url.strip()
            if not url:
                continue  # Skip empty lines

            try:
                # Extract file ID from URL
                if '/d/' in url:
                    file_id = url.split('/d/')[1].split('/')[0]
                else:
                    raise ValueError(f"Invalid URL format: {url}")

                print(f"Processing URL: {url}, extracted file ID: {file_id}")

                file_metadata = drive_service.files().get(fileId=file_id, fields='mimeType, name').execute()
                mime_type = file_metadata.get('mimeType')
                file_name = file_metadata.get('name')

                print(f"File name: {file_name}, MIME type: {mime_type}")

                file_content = download_file_from_drive(file_id)
                if file_content:
                    output_pdf_path = os.path.join(output_dir, f"{file_name}.pdf")
                    if os.path.exists(output_pdf_path):
                        print(f"File {output_pdf_path} already exists. Skipping conversion.")
                        continue
                    try:
                        convert_to_pdf(file_content, output_dir, file_name)
                        print(f"Successfully converted {file_name} to {output_pdf_path}")
                    except subprocess.CalledProcessError as e:
                        print(f"Conversion failed for {file_name}: {e.stderr}")
                    except Exception as e:
                        print(f"Error during conversion: {e}")
                else:
                    print(f"Failed to download file: {file_name}")

            except ValueError as ve:
                print(f"Error: {ve}")
                continue  # Continue to the next URL
            except Exception as e:
                print(f"Error processing URL {url}: {e}")


# --- Main Execution ---
input_file_path = "/usr/local/google/home/stefanward/DriveFileStream/Other computers/My Mac/projects/pyscripts/con2pdf/test.docx";  # Replace with the path to your inputfile.txt
output_dir = "/usr/local/google/home/stefanward/DriveFileStream/Other computers/My Mac/projects/pyscripts/con2pdf/converts";  # Replace with the path to your output directory

process_drive_files(input_file_path, output_dir);

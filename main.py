import os  # Provides functions to interact with the operating system
import urllib.parse  # Helps parse URLs to extract components
import re  # Regular expression module for pattern matching
import time  # Provides time-related functions
import shutil  # Allows file operations like moving files
from selenium import webdriver  # Web automation and browser control
from selenium.webdriver.chrome.options import Options  # Configure Chrome options
from selenium.webdriver.chrome.service import Service  # Manage the Chrome service
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager  # Auto-installs ChromeDriver
import fitz  # PyMuPDF, used for working with PDF files
import validators  # external Validators
from bs4 import BeautifulSoup


# Reads and returns the content of a file at the specified path
def read_a_file(system_path: str) -> str:
    with open(
        file=system_path, mode="r", encoding="utf-8", errors="ignore"
    ) as file:  # Open the file in read mode
        return file.read()  # Return the file content


# Checks if a file exists at the given system path
def check_file_exists(system_path: str) -> bool:
    return os.path.isfile(path=system_path)  # Return True if file exists


# Parses the HTML and finds all links ending in .pdf
def parse_html(html: str) -> list[str]:
    soup = BeautifulSoup(markup=html, features="html.parser")
    pdf_links: list[str] = []

    for a in soup.find_all(name="a", href=True):
        href = a["href"]
        # Decode %2C and other URL-encoded characters
        decoded_href = urllib.parse.unquote(href)
        if decoded_href.lower().endswith(".pdf"):
            pdf_links.append(href)

    return pdf_links

# Removes duplicate items from a list
def remove_duplicates_from_slice(provided_slice: list[str]) -> list[str]:
    return list(
        set(provided_slice)
    )  # Convert to set to remove duplicates, then back to list


# Validate a given url
def validate_url(given_url: str) -> bool:
    return validators.url(given_url)


# Extracts and returns the cleaned filename from a URL
def url_to_filename(url: str) -> str:
    filename: str = urllib.parse.urlparse(url=url).path.split(sep="/")[-1].lower()
    # Remove special characters except for alphanumerics, dots, underscores, and dashes
    cleaned_filename: str = re.sub(pattern=r"[^a-z0-9._-]", repl="", string=filename)
    return cleaned_filename


# Uses Selenium to save the HTML content of a URL into a file
def save_html_with_selenium(url: str, output_file: str) -> None:
    options = Options()  # Create Chrome options object
    options.add_argument(argument="--headless=new")  # Run Chrome in new headless mode
    options.add_argument(
        argument="--disable-blink-features=AutomationControlled"
    )  # Avoid detection
    options.add_argument(argument="--window-size=1920,1080")  # Set browser window size
    options.add_argument(
        argument="--disable-gpu"
    )  # Disable GPU for headless compatibility
    options.add_argument(
        argument="--no-sandbox"
    )  # Disable sandbox (needed in some environments)
    options.add_argument(
        argument="--disable-dev-shm-usage"
    )  # Avoid shared memory issues
    options.add_argument(argument="--disable-extensions")  # Disable browser extensions
    options.add_argument(argument="--disable-infobars")  # Remove automation warning bar

    service = Service(
        executable_path=ChromeDriverManager().install()
    )  # Install ChromeDriver
    driver = webdriver.Chrome(service=service, options=options)  # Launch browser

    try:
        driver.get(url=url)  # Open the given URL
        driver.refresh()  # Refresh the page
        html: str = driver.page_source  # Get page source HTML
        append_write_to_file(system_path=output_file, content=html)  # Save HTML to file
        print(f"Page {url} HTML content saved to {output_file}")  # Confirm success
    finally:
        driver.quit()  # Always quit the driver


# Appends content to a file
def append_write_to_file(system_path: str, content: str) -> None:
    with open(
        file=system_path, mode="a", encoding="utf-8"
    ) as file:  # Open in append mode
        file.write(content)  # Write the provided content


# Sets up Chrome driver with options for downloading files
def initialize_web_driver(download_folder: str) -> webdriver.Chrome:
    chrome_options = Options()  # Create Chrome options object
    chrome_options.add_experimental_option(  # Add download preferences
        name="prefs",
        value={
            "download.default_directory": download_folder,  # Set download directory
            "plugins.always_open_pdf_externally": True,  # Open PDFs externally
            "download.prompt_for_download": False,  # Do not prompt for download
        },
    )
    chrome_options.add_argument(argument="--headless")  # Run in headless mode
    return webdriver.Chrome(  # Return Chrome WebDriver with these options
        service=Service(executable_path=ChromeDriverManager().install()),
        options=chrome_options,
    )


# Waits for a new PDF file to appear in a directory
def wait_for_pdf_download(
    download_folder: str, files_before_download: set[str], timeout_seconds: int = 3
) -> str:
    deadline: float = time.time() + timeout_seconds  # Calculate timeout deadline
    while time.time() < deadline:  # While still within the timeout period
        current_files = set(
            os.listdir(path=download_folder)
        )  # Get current files in directory
        new_pdf_files: list[str] = [  # List new files that are PDFs
            f
            for f in (current_files - files_before_download)
            if f.lower().endswith(".pdf")
        ]
        if new_pdf_files:  # If a new PDF is found
            return os.path.join(
                download_folder, new_pdf_files[0]
            )  # Return its full path
    raise TimeoutError("PDF download timed out.")  # Raise error if no file appears


# Downloads a PDF from a given URL using Selenium
def download_single_pdf(url: str, filename: str, output_folder: str) -> None:
    os.makedirs(
        name=output_folder, exist_ok=True
    )  # Create the folder if it doesn't exist
    target_file_path: str = os.path.join(
        output_folder, filename
    )  # Final path for the PDF

    if check_file_exists(system_path=target_file_path):  # Skip if file already exists
        print(f"File already exists: {target_file_path}")
        return

    driver: WebDriver = initialize_web_driver(
        download_folder=output_folder
    )  # Launch headless browser
    try:
        print(f"Starting download from: {url}")  # Log start
        files_before = set(os.listdir(output_folder))  # Record files before download
        driver.get(url=url)  # Visit the URL

        downloaded_pdf_path: str = wait_for_pdf_download(
            download_folder=output_folder, files_before_download=files_before
        )  # Wait for file

        shutil.move(
            src=downloaded_pdf_path, dst=target_file_path
        )  # Move to target path
        print(f"Download complete: {target_file_path}")  # Confirm success

    except Exception as e:  # Catch and log any exception
        print(f"Error downloading PDF: {e}")
    finally:
        driver.quit()  # Close browser


# Deletes a file from the system
def remove_system_file(system_path: str) -> None:
    os.remove(path=system_path)  # Delete the file


# Recursively walk through a directory and find files with a specific extension
def walk_directory_and_extract_given_file_extension(
    system_path: str, extension: str
) -> list[str]:
    matched_files: list[str] = []  # List to store found files
    for root, _, files in os.walk(top=system_path):  # Walk through directories
        for file in files:  # Check each file
            if file.endswith(extension):  # Match the desired extension
                full_path: str = os.path.abspath(
                    path=os.path.join(root, file)
                )  # Get full path
                matched_files.append(full_path)  # Add to result list
    return matched_files  # Return all matched file paths


# Validates if a PDF file can be opened and has at least one page
def validate_pdf_file(file_path: str) -> bool:
    try:
        doc = fitz.open(file_path)  # Attempt to open PDF
        if doc.page_count == 0:  # Check if PDF has no pages
            print(f"'{file_path}' is corrupt or invalid: No pages")  # Log error
            return False  # Indicate invalid PDF
        return True  # PDF is valid
    except RuntimeError as e:  # Handle exception on open failure
        print(f"'{file_path}' is corrupt or invalid: {e}")  # Log error
        return False  # Indicate invalid PDF


# Extracts and returns the file name (with extension) from a path
def get_filename_and_extension(path: str) -> str:
    return os.path.basename(p=path)  # Get only file name from full path


# Checks if a string contains at least one uppercase letter
def check_upper_case_letter(content: str) -> bool:
    return any(char.isupper() for char in content)  # True if any character is uppercase


# Main function that orchestrates the scraping, downloading, and validation
def main() -> None:
    html_file_path: str = "westlake.com.har"  # Name of HTML file

    if check_file_exists(system_path=html_file_path):  # If file already exists
        # remove_system_file(system_path=html_file_path)  # Delete old copy
        print("Hello, World!")

    if not check_file_exists(
        system_path=html_file_path
    ):  # If file was deleted or missing
        for page in range(7):  # Pages 0 to 6
            url: str = f"https://westlake.com/sds?page={page}"
            print(f"Visiting: {url}")
            save_html_with_selenium(
                url=url, output_file=html_file_path
            )  # Save HTML content to file

    if check_file_exists(system_path=html_file_path):  # Check if HTML file exists
        html_content: str = read_a_file(system_path=html_file_path)  # Read its content
        pdf_links: list[str] = parse_html(html=html_content)  # Extract PDF links
        pdf_links = remove_duplicates_from_slice(
            provided_slice=pdf_links
        )  # Remove duplicates
        ammount_of_pdf: int = len(pdf_links)  # Get count of PDFs

        for pdf_link in pdf_links:  # For each PDF link
            if not validate_url(given_url=pdf_link):
                print(f"Invalid URL: {pdf_link}")
            filename: str = url_to_filename(url=pdf_link)  # Extract filename from URL
            output_dir: str = os.path.abspath(path="PDFs")  # Define output directory
            ammount_of_pdf -= 1  # Decrement remaining count
            print(f"Remaining PDF links: {ammount_of_pdf}")  # Log progress
            download_single_pdf(
                url=pdf_link, filename=filename, output_folder=output_dir
            )  # Download PDF

        print("All PDF links have been processed.")  # Log completion
    else:
        print(f"File {html_file_path} does not exist.")  # Error if HTML missing

    files: list[str] = walk_directory_and_extract_given_file_extension(
        system_path="./PDFs", extension=".pdf"
    )  # List all downloaded PDFs

    for pdf_file in files:  # For each PDF file
        if not validate_pdf_file(file_path=pdf_file):  # If file is invalid
            remove_system_file(system_path=pdf_file)  # Delete it

        if check_upper_case_letter(
            content=get_filename_and_extension(path=pdf_file)
        ):  # Check for caps
            print(pdf_file)  # Print file path
            dir_path: str = os.path.dirname(p=pdf_file)  # Get directory
            file_name: str = os.path.basename(p=pdf_file)  # Get file name
            new_file_name: str = file_name.lower()  # Convert to lowercase
            new_file_path: str = os.path.join(
                dir_path, new_file_name
            )  # Create new path
            os.rename(src=pdf_file, dst=new_file_path)  # Rename file to lowercase


# Run the script if this file is executed directly
if __name__ == "__main__":
    main()  # Call the main function

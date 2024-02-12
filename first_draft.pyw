import requests
from bs4 import BeautifulSoup
import ctypes

# Get the website content
response = requests.get("https://www.myprotein.co.il/")
response.raise_for_status()  # Will raise an error if the GET request fails

# Parse the content using BeautifulSoup
soup = BeautifulSoup(response.text, "html.parser")

# Find the string with discount.
# This might need adjusting based on actual website structure.
discount = None
for string in soup.strings:
    if "% off" in string:
        # Extract the last word before the '%' sign, which should be the discount number
        discount_string = string.split("%")[0].split()[-1].strip()
        try:
            discount = int(discount_string)
            break
        except ValueError:
            print(f"error in string: {discount_string}")
            continue  # This will handle cases where the conversion to int fails

if discount:
    # If you want to display an alert only if the discount is greater than a certain amount:
    # Uncomment the next line and replace 20 with your desired threshold
    # if discount > 20:
    ctypes.windll.user32.MessageBoxW(
        0,
        f"My Protein has a {discount}% discount today",
        "My Protein Discount Alert",
        0x40 | 0x1,
    )
else:
    ctypes.windll.user32.MessageBoxW(
        0, "No discount found today.", "My Protein Discount Alert", 0x40 | 0x1
    )
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox
import mplcursors
from matplotlib.dates import num2date
import math
import numpy as np
import sys
import re

target_site = "https://www.myprotein.co.il"
WAFER_URL = "https://www.myprotein.co.il/p/sports-nutrition/crispy-protein-wafer/10961185/"

def fetch_discount():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(target_site, headers=headers, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    candidates = []
    for string in soup.stripped_strings:
        text = string.strip()
        lower = text.lower()

        # Focus on actual discount copy and skip less-relevant promo text
        if "off" not in lower:
            continue
        if "app" in lower or "first order" in lower or "new" in lower:
            continue

        for match in re.finditer(r"(\d{1,2})\s*%", text):
            try:
                candidates.append(int(match.group(1)))
            except ValueError:
                pass

    if not candidates:
        return None

    return max(candidates)

def scrape_product_price(url):
    # Send a GET request to the URL
    response = requests.get(url)
    # Raise an exception if the request was unsuccessful
    response.raise_for_status()

    # Parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")

    # DEBUG: Search for span elements with price-related classes
    print("\n=== Searching for span elements with 'price' in class ===")
    price_spans = soup.find_all("span", class_=lambda x: x and "price" in x.lower())
    for i, span in enumerate(price_spans):
        print(f"Span {i}: class='{span.get('class')}', text='{span.text.strip()}'")
    
    # Extract price from the first price span
    if price_spans:
        first_price_text = price_spans[0].text.strip()
        print(f"\nFirst price text: '{first_price_text}'")
        
        # Extract just the numeric part (before any spaces/symbols)
        price_str = first_price_text.split()[0]  # Gets "117.70" from "117.70 âªâ"
        print(f"Extracted price string: '{price_str}'")
        
        try:
            price = float(price_str)
            print(f"SUCCESS: Extracted price {price}")
            return price
        except Exception as e:
            print(f"Failed to convert '{price_str}' to float: {e}")
    
    print("Failed to find price")
    return None

def fetch_usd_to_nis_rate():
    """Fetch current USD to NIS exchange rate from a free API."""
    try:
        response = requests.get("https://open.er-api.com/v6/latest/USD")
        response.raise_for_status()
        data = response.json()
        return data["rates"]["ILS"]
    except Exception as e:
        # Fallback to approximate rate if API fails
        print(f"Failed to fetch exchange rate: {e}")
        return 3.7  # Approximate fallback rate

def calculate_max_units(base_price, discount_percent, usd_to_nis_rate, usd_limit=75):
    """Calculate maximum units that can be bought under the USD limit.
    
    Args:
        base_price: Base price in NIS
        discount_percent: Discount percentage (e.g., 20 for 20%)
        usd_to_nis_rate: Current USD to NIS exchange rate
        usd_limit: Maximum USD budget (default 75)
    
    Returns:
        tuple: (max_units, total_price_nis, total_price_usd)
    """
    # Apply the discount
    discounted_price = base_price * (1 - discount_percent / 100)
    # Apply additional 10% off
    final_unit_price = discounted_price * 0.9
    # Convert USD limit to NIS
    nis_limit = usd_limit * usd_to_nis_rate
    # Calculate max units
    max_units = int(nis_limit / final_unit_price)
    # Calculate actual total
    total_price_nis = max_units * final_unit_price
    total_price_usd = total_price_nis / usd_to_nis_rate
    
    return max_units, total_price_nis, total_price_usd

def update_csv(discount, protein_powder_price):
    today = datetime.now().strftime("%Y-%m-%d")
    filename = "discount_data.csv"
    try:
        df = pd.read_csv(filename)
        if today not in df["Date"].values:
            df = pd.concat([df, pd.DataFrame([{
                    "Date": today,
                    "Discount": discount,
                    "Protein Powder Price": protein_powder_price,
                }])], ignore_index=True)
            df.to_csv(filename, index=False)
        else:
            pass
    except FileNotFoundError:
        df = pd.DataFrame(
            {
                "Date": [today],
                "Discount": [discount],
                "Protein Powder Price": [protein_powder_price],
            }
        )
        df.to_csv(filename, index=False)

def plot_graph():
    df = pd.read_csv("discount_data.csv")
    df["Date"] = pd.to_datetime(df["Date"])  # Ensure 'Date' column is datetime dtype
    df.sort_values("Date", inplace=True)  # Ensure data is sorted by date

    fig, ax = plt.subplots()
    # Create a step plot
    (line,) = ax.step(
        df["Date"], df["Discount"], where="post", linestyle="-", linewidth=2
    )

    # Set up the plot aesthetics
    ax.set_xlabel("Date")
    ax.set_ylabel("Discount (%)")
    ax.grid(True)  # Adds the grid
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Customize the cursor
    cursor = mplcursors.cursor(line, hover=True)

    @cursor.connect("add")
    def on_add(sel):
        # Convert the Matplotlib date number to a datetime object
        date = num2date(sel.target[0])
        date = datetime(date.year, date.month, date.day)
        date_str = date.strftime("%Y-%m-%d")
        # Retrieve the index of the selected point
        point_index = sel.index
        # Get the data from the line
        xdata, ydata = line.get_data()

        try:
            discount = ydata[np.where(xdata == np.datetime64(date))[0][0]]

            # Customize the annotation text
            sel.annotation.set_text(f"Date: {date_str}\nDiscount: {discount}%")
            # Customize the background color
            sel.annotation.get_bbox_patch().set_facecolor("lightblue")
            # Customize the text color
            sel.annotation.get_bbox_patch().set_alpha(0.5)
        except Exception as e:
            print(f"datetime64: {np.datetime64(date)}")
            print(f"point index x: {point_index.x}")
            print(f"point index y: {point_index.y}")
            print(f"xdata: {xdata}")
            # print(f"ydata: {ydata}")
            print(f"where: {np.where(xdata == np.datetime64(date))}\n")
            print(f"Exception: {e}")
            pass

    # Handling clicks to show more information in a new window
    def on_click(event):
        if event.dblclick:
            info_window = tk.Tk()
            info_window.title("More Information")
            tk.Label(
                info_window,
                text=f'More info about the discount on {event.xdata.strftime("%Y-%m-%d")}:\nDiscount was {event.ydata}%',
            ).pack()
            info_window.mainloop()

    fig.canvas.mpl_connect("button_press_event", on_click)

    plt.show()

def main():
    # protein_powder_price returned None for some reason and that broke the following code
    # but I am too lazy to fix it and it might be redundant anyway so I will just set it to 0
    protein_powder_price = 0
    wafer_url = "https://www.myprotein.co.il/p/sports-nutrition/crispy-protein-wafer/10961185/"
    
    # Fetch discount
    fail_count = 0
    for i in range(3):
        try:
            discount = fetch_discount()
        except Exception as e:
            fail_count += 1
    if fail_count == 3:
        messagebox.showinfo("Error", f"{e}")
        sys.exit(1)

    print(f"Discount: {discount}")
    print(f"Protein Powder Price: {protein_powder_price}")
    
    # Fetch exchange rate and wafer price
    usd_to_nis = None
    wafer_price = None
    max_units = 0
    total_nis = 0
    total_usd = 0
    
    try:
        usd_to_nis = fetch_usd_to_nis_rate()
        print(f"Exchange Rate: 1 USD = {usd_to_nis:.2f} NIS")
    except Exception as e:
        print(f"Failed to fetch exchange rate: {e}")
    
    try:
        wafer_price = scrape_product_price(wafer_url)
        print(f"Wafer Price: {wafer_price} NIS")
    except Exception as e:
        print(f"Failed to fetch wafer price: {e}")
    
    # Calculate max units if we have all the data
    if discount and wafer_price and usd_to_nis:
        max_units, total_nis, total_usd = calculate_max_units(wafer_price, discount, usd_to_nis)
        print(f"Max Units: {max_units}")
        print(f"Total: {total_nis:.2f} NIS ({total_usd:.2f} USD)")
        
    if discount is not None and protein_powder_price is not None:
        update_csv(discount, protein_powder_price)
        root = tk.Tk()
        root.withdraw()
        
        # Build message with discount and wafer info
        message = f"My Protein has a {discount}% discount today."
        
        if max_units > 0:
            # message += f"\n\nYou can buy {max_units} units of Crispy Protein Wafer for under 75 USD."
            # message += f"\nTotal: {total_nis:.2f} ₪ (≈{total_usd:.2f} USD)"
            # message += f"\nPrice per unit after discounts: {total_nis/max_units:.2f} ₪"
            # message += f"\n\nTo stay under 75 USD, thats {max_units} wafers for {total_nis:.2f}₪ (≈{total_usd:.2f} USD) • {total_nis/max_units:.2f}₪ each"
            message += f" Thats {max_units} Protein Wafers."
            message += f"\n\n75 USD is {usd_to_nis*75:.2f}₪, {max_units} wafers is {total_nis:.2f}₪ ({total_nis/max_units:.2f}₪ each)"
        
        message += "\n\nWould you like to see the discount trend graph?"
        
        if messagebox.askyesno("My Protein Discount Alert", message):
            plot_graph()
        root.destroy()
    else:
        messagebox.showinfo("My Protein Discount Alert", "No discount found today.")


if __name__ == "__main__":
    main()
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

target_site = "https://www.myprotein.co.il"

def fetch_discount():
    response = requests.get(target_site)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    discount = None
    for string in soup.strings:
        if "% off" in string:
            discount_string = string.split("%")[0].split()[-1].strip()
            try:
                discount = int(discount_string)
                break
            except ValueError:
                continue
    return discount

def scrape_product_price(url):
    # Send a GET request to the URL
    response = requests.get(url)
    # Raise an exception if the request was unsuccessful
    response.raise_for_status()

    # Parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")

    # Use a regex pattern to find the price
    # The pattern assumes that the price is formatted like "123 ₪" within the text
    for string in soup.strings:
        if " ₪" in string:
            splits = string.split(" ")
            for curr_split in splits:
                try:
                    return float(curr_split)
                except:
                    pass
    return None

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
    protein_powder_price = scrape_product_price(
        target_site
        + "/sports-nutrition/impact-whey-protein/10530943.html?switchcurrency=ILS&variation=12309347"
    )
    # protein_brownie_price
    fail_count = 0
    for i in range(3):
        try:
            discount = fetch_discount()
        except Exception as e:
            fail_count += 1
    if fail_count == 3:
        messagebox.showinfo("Error", f"{e}")
        sys.exit(1)
        
    if discount is not None and protein_powder_price is not None:
        update_csv(discount, protein_powder_price)
        root = tk.Tk()
        root.withdraw()
        if messagebox.askyesno(
            "My Protein Discount Alert",
            f"My Protein has a {discount}% discount today.\nWould you like to see the discount trend graph?",
        ):
            plot_graph()
        root.destroy()
    else:
        messagebox.showinfo("My Protein Discount Alert", "No discount found today.")


if __name__ == "__main__":
    main()
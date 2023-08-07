import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import pandas as pd
from io import BytesIO
import requests
from PIL import Image
from reportlab.lib.utils import ImageReader
from urllib.parse import urlparse, urlunparse

#fetching credentials from st.secrets
#creds = st.secrets

# Function to fetch data from Google Sheet
def get_data_from_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = st.secrets
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds, scope)
    #creds = gspread.service_account_from_dict(creds)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name)
    '''data_sheet3 = sheet.worksheet("Master - Inventory").get_all_records()
    data_sheet5 = sheet.worksheet("Sneaker Product Template").get_all_values()'''
    data_sheet3 = sheet.get_worksheet(0).get_all_records()
    data_sheet5 = sheet.get_worksheet(1).get_all_values()
    return data_sheet3, data_sheet5

# Function to convert PIL Image to PNG format
def convert_to_png(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()  # Return the bytes of the PNG image

# Function to fetch images from URLs
def fetch_images_from_urls(image_links):
    images = []
    for link in image_links:
        response = requests.get(link)
        if response.status_code == 200:
            try:
                image = Image.open(BytesIO(response.content))
                images.append(image)
            except Exception as e:
                print(f"Error in opening image: {e}")
    return images

# Function to generate PDF
def generate_pdf(data, images):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Add filtered data and images to the PDF
    for item, image in zip(data, images):
        c.drawString(100, 700, f"Product List: {item['Product List']}")
        c.drawString(100, 680, f"Size: {item['Size']}")
        c.drawString(100, 660, f"Site: {item['Site']}")
        if image:
            # Convert PIL Image to PNG format and read as ImageReader
            image_bytes = convert_to_png(image)
            img_reader = ImageReader(image_bytes)
            c.drawImage(img_reader, 100, 100, width=200, height=200)
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer

def main():
    st.title("Sneaker Reselling Catalog Generator")
    data_sheet3, data_sheet5 = get_data_from_google_sheet("Copy - MNSt | Inventory Master - Active")
    df_sheet3 = pd.DataFrame(data_sheet3)
    columns_ds5 = data_sheet5[0]
    data_sheet5 = data_sheet5[1:]
    df_sheet5 = pd.DataFrame(data_sheet5, columns=columns_ds5)
    # Drop duplicate 'Style Code 1' columns in df_sheet5 (if any)
    df_sheet5 = df_sheet5.loc[:, ~df_sheet5.columns.duplicated()]
    print(df_sheet3.columns)
    

    # Filter options
    product_name_filter = st.sidebar.text_input("Enter Product Name (Product List):")
    size_filter = st.sidebar.selectbox("Select Size:", df_sheet3['Size'].unique())
    location_filter = st.sidebar.selectbox("Select Location:", ["Mumbai", "Delhi"])

    if st.button('Generate Catalog'):
        # Apply filters on Sheet3
        filtered_data = df_sheet3

        if product_name_filter:
            filtered_data = filtered_data[filtered_data['Product List'].str.contains(product_name_filter, case=False)]

        if size_filter:
            filtered_data = filtered_data[filtered_data['Size'] == size_filter]

        if location_filter == "Mumbai":
            filtered_data = filtered_data[filtered_data['Site'].str.startswith("BOM")]

        if location_filter == "Delhi":
            filtered_data = filtered_data[filtered_data['Site'].str.startswith("DEL")]

        # Filter based on Status column (keep only "Available" rows)
        filtered_data = filtered_data[filtered_data['Status'] == "Available"]

        # Merge with Sheet5 to get image links
        filtered_data = pd.merge(filtered_data, df_sheet5[['Style Code 1', 'image_0']], left_on='Style Code*', right_on='Style Code 1', how='left')

        # Ensure all elements in the list are strings
        imagelinks = list(map(str, filtered_data["image_0"].tolist()))

        # Process the links and create the new list
        imagelinks = [link[:link.find(".jpg") + 4] if ".jpg" in link else link for link in imagelinks]
        imagelinks = imagelinks[:-1]
        print(imagelinks)
        images = fetch_images_from_urls(imagelinks)
        #images = fetch_images_from_urls([urlparse(link)._replace(query="").geturl() for link in filtered_data["image_0"]])
        pdf_buffer = generate_pdf(filtered_data.to_dict('records'), images)
        st.success("Catalog generated! Click the link below to download.")
        st.download_button("Download Catalog", pdf_buffer, file_name="catalog.pdf")

if __name__ == "__main__":
    main()

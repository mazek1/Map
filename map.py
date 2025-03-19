import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import os

# Initialize Streamlit app
st.title("Shop Location Mapper")
st.write("Upload an Excel file with shop details to generate an interactive map.")

# Define session state storage file
DATA_FILE = "shop_data.xlsx"

# File uploader
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.to_excel(DATA_FILE, index=False)  # Save uploaded file
    st.success("File uploaded and saved.")
elif os.path.exists(DATA_FILE):
    df = pd.read_excel(DATA_FILE)
    st.info("Using previously uploaded data.")
else:
    df = None
    st.warning("No file uploaded yet.")

if df is not None:
    # Ensure required columns exist
    required_columns = ["Company", "City", "Country"]
    if not all(col in df.columns for col in required_columns):
        st.error("The file must contain at least 'Company', 'City', and 'Country' columns.")
    else:
        # Geocoding function
        geolocator = Nominatim(user_agent="shop_locator")
        
        @st.cache_data
        def get_coordinates(city, country):
            try:
                location = geolocator.geocode(f"{city}, {country}", timeout=10)
                if location:
                    return location.latitude, location.longitude
            except GeocoderTimedOut:
                time.sleep(1)
                return get_coordinates(city, country)
            return None, None
        
        # Add latitude and longitude columns if missing
        if "Latitude" not in df.columns or "Longitude" not in df.columns:
            df[['Latitude', 'Longitude']] = df.apply(
                lambda row: pd.Series(get_coordinates(row['City'], row['Country'])), axis=1
            )
            df.to_excel(DATA_FILE, index=False)  # Save geocoded data
        
        # Remove rows with missing coordinates
        df = df.dropna(subset=['Latitude', 'Longitude'])
        
        # Generate map
        st.write("### Interactive Map of Shops")
        shop_map = folium.Map(location=[50, 10], zoom_start=4)
        marker_cluster = MarkerCluster().add_to(shop_map)
        
        for _, row in df.iterrows():
            popup_text = f"""
            <b>{row['Company']}</b><br>
            {row['City']}, {row['Country']}<br>
            """
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=popup_text,
                tooltip=row['Company']
            ).add_to(marker_cluster)
        
        # Display map
        st.components.v1.html(shop_map._repr_html_(), height=800)
        
        # Display data table
        st.write("### Shop Data")
        st.dataframe(df)

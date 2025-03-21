import streamlit as st
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import os
import streamlit.components.v1 as components

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
    required_columns = ["Company", "City", "Country", "Address"]
    if not all(col in df.columns for col in required_columns):
        st.error("The file must contain at least 'Company', 'City', 'Country', and 'Address' columns.")
    else:
        # Remove unwanted entries
        df = df[~df['Company'].str.contains("personale", case=False, na=False)]
        df = df[~df['Address'].str.contains("mosevej", case=False, na=False)]

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

        # --- Search Bar Below Heading ---
        search_query = st.text_input("Search for a customer by name")
        selected_row = None
        if search_query:
            matches = df[df['Company'].str.contains(search_query, case=False, na=False)]
            if not matches.empty:
                selected_row = matches.iloc[0]
                st.success(f"Found: {selected_row['Company']} in {selected_row['City']}, {selected_row['Country']}")
            else:
                st.warning("No matching customer found.")

        map_center = [selected_row['Latitude'], selected_row['Longitude']] if selected_row is not None else [50, 10]
        zoom_level = 10 if selected_row is not None else 4
        shop_map = folium.Map(location=map_center, zoom_start=zoom_level)

        countries = df['Country'].unique()
        country_groups = {}

        for country in countries:
            country_data = df[df['Country'] == country]

            if country == "Germany" and "State" in df.columns:
                states = country_data['State'].unique()
                for state in states:
                    state_data = country_data[country_data['State'] == state]
                    group_name = f"{state} (Germany)"
                    country_groups[group_name] = folium.FeatureGroup(name=group_name)
                    for _, row in state_data.iterrows():
                        popup_text = f"""
                        <b>{row['Company']}</b><br>
                        {row['City']}, {row['State']}, {row['Country']}<br>
                        {row.get('Address', '')}<br>
                        {row.get('Email', '')}<br>
                        {row.get('Phone', '')}<br>
                        """
                        marker = folium.Marker(
                            location=[row['Latitude'], row['Longitude']],
                            popup=popup_text,
                            tooltip=row['Company']
                        )
                        marker.add_to(country_groups[group_name])
                        if selected_row is None and search_query == row['Company']:
                            selected_row = row
            else:
                country_groups[country] = folium.FeatureGroup(name=country)
                for _, row in country_data.iterrows():
                    popup_text = f"""
                    <b>{row['Company']}</b><br>
                    {row['City']}, {row['Country']}<br>
                    {row.get('Address', '')}<br>
                    {row.get('Email', '')}<br>
                    {row.get('Phone', '')}<br>
                    """
                    marker = folium.Marker(
                        location=[row['Latitude'], row['Longitude']],
                        popup=popup_text,
                        tooltip=row['Company']
                    )
                    marker.add_to(country_groups[country])
                    if selected_row is None and search_query == row['Company']:
                        selected_row = row

        for group in country_groups.values():
            shop_map.add_child(group)

        folium.LayerControl().add_to(shop_map)

        # Display map with equal width and height
        components.html(shop_map._repr_html_(), height=1000, width=1000)

        # Display selected customer info below map
        if selected_row is not None:
            st.write("### Selected Customer Details")
            st.write(f"**Company**: {selected_row['Company']}")
            st.write(f"**City**: {selected_row['City']}")
            st.write(f"**Country**: {selected_row['Country']}")

            address = selected_row.get('Address', 'N/A')
            search_url = f"https://www.google.com/search?q={address.replace(' ', '+')}"
            st.markdown(f"**Address**: [{address}]({search_url})", unsafe_allow_html=True)

            st.write(f"**Email**: {selected_row.get('Email', 'N/A')}")
            st.write(f"**Phone**: {selected_row.get('Phone', 'N/A')}")

        # Display data table
        st.write("### Shop Data")
        st.dataframe(df)

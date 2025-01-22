from shiny import App, render, ui
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

# Step 1: Load and preprocess data
### will wd
acled_file_path = '/Users/willsigal/Desktop/UChicago/Fall 2025/Python Final/2013-01-01-2024-01-01-Central_America.csv'
shapefile_path = '/Users/willsigal/Documents/GitHub/Final-Project/CA_shape_files/ca_admin_boundaries1.shp'
### andy wd
#acled_file_path = 'd:\\UChicago\\Classes\\2024Qfall\\Programming Python\\Final-Project\\Data\\2013-01-01-2024-01-01-Central_America.csv'
#shapefile_path = 'd:\\UChicago\\Classes\\2024Qfall\\Programming Python\\Final-Project\\CA_shape_files\\ca_admin_boundaries1.shp'

# Load datasets
acled_2013 = pd.read_csv(acled_file_path)
ca_gdf = gpd.read_file(shapefile_path)

# Preprocess data
events_gdf = gpd.GeoDataFrame(
    acled_2013,
    geometry=gpd.points_from_xy(acled_2013['longitude'], acled_2013['latitude']),
    crs="EPSG:4326"
)
ca_gdf = ca_gdf.to_crs(events_gdf.crs)

# Perform spatial join
events_with_boundaries = gpd.sjoin(events_gdf, ca_gdf, how="left", predicate="within")
events_with_boundaries['country'] = events_with_boundaries['country_right']  # Ensure country is preserved

# Extract unique event types
event_types = ["All"] + events_with_boundaries['event_type'].dropna().unique().tolist()
countries = ["All"] + ca_gdf["country"].dropna().unique().tolist()

#  UI
app_ui = ui.page_fluid(
    ui.h2("Central America Events Visualization"),
    ui.row(
        ui.column(
            6,
            ui.input_select("country_selector", "Select a Country", choices=countries),
            ui.input_select("event_type_selector", "Select Event Type", choices=event_types)
        )
    ),
    ui.row(
        ui.column(
            3,  
            ui.h3("Summary Statistics"),
            ui.output_text_verbatim("summary_stats")
        ),
        ui.column(
            9,  
            ui.output_plot("map_plot", height="600px"),
        )
    )
)

def server(input, output, session):
    @output
    @render.plot
    def map_plot():
        # Filter events based on country and event type
        filtered_events = events_with_boundaries.copy()
        if input.country_selector() != "All":
            filtered_events = filtered_events[filtered_events["country"] == input.country_selector()]
        if input.event_type_selector() != "All":
            filtered_events = filtered_events[filtered_events['event_type'] == input.event_type_selector()]

        # Filter for 2018 and 2023
        events_filtered = filtered_events[filtered_events['year'].isin([2018, 2023])]

        # Aggregate events
        events_agg = events_filtered.groupby(['boundary_i', 'year']).size().unstack(fill_value=0).reset_index()
        events_agg.columns = ['boundary_i', 'events_2018', 'events_2023']

        # Merge with shapefile
        filtered_data = ca_gdf.merge(events_agg, on='boundary_i', how='left')
        filtered_data['events_2018'] = filtered_data['events_2018'].fillna(0)
        filtered_data['events_2023'] = filtered_data['events_2023'].fillna(0)

        # Calculate percent change
        filtered_data['percent_change'] = (
            (filtered_data['events_2023'] - filtered_data['events_2018']) /
            filtered_data['events_2018'].replace(0, np.nan)
        ) * 100
        filtered_data['percent_change'] = filtered_data['percent_change'].replace([np.inf, -np.inf], np.nan)
        filtered_data['percent_change'] = filtered_data['percent_change'].fillna(0).clip(lower=-500, upper=500)

        # Identify areas with zero events in both years
        zero_events = filtered_data[(filtered_data['events_2018'] == 0) & (filtered_data['events_2023'] == 0)]
        non_zero_events = filtered_data[~((filtered_data['events_2018'] == 0) & (filtered_data['events_2023'] == 0))]

        # Plot the data
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))

        # Adjust the base map depending on the selected country
        if input.country_selector() != "All":
            # Subset the base map to the selected country
            base_gdf = ca_gdf[ca_gdf['country'] == input.country_selector()]
            base = base_gdf.plot(color='white', edgecolor='black', linewidth=0.5, ax=ax)
            # Adjust the axis limits to the selected country
            xmin, ymin, xmax, ymax = base_gdf.total_bounds
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymin, ymax)
        else:
            base = ca_gdf.plot(color='white', edgecolor='black', linewidth=0.5, ax=ax)

        # Plot non-zero events with percent_change
        if not non_zero_events.empty:
            non_zero_events.plot(
                column='percent_change',
                cmap='RdBu',
                linewidth=0.5,
                edgecolor='black',
                legend=True,
                ax=base,
                vmin=-500,
                vmax=500
            )

        
        if not zero_events.empty:
            zero_events.plot(
                color='gray',
                linewidth=0.5,
                edgecolor='black',
                ax=base
            )

        ax.set_title('Percent Change in Events (2018-2023)', fontsize=16)
        ax.set_axis_off()
        return fig

    @output
    @render.text
    def summary_stats():
        # Filter events based on country and event type
        filtered_events = events_with_boundaries.copy()
        if input.country_selector() != "All":
            filtered_events = filtered_events[filtered_events["country"] == input.country_selector()]
        if input.event_type_selector() != "All":
            filtered_events = filtered_events[filtered_events['event_type'] == input.event_type_selector()]

        # Filter for 2018 and 2023
        events_filtered = filtered_events[filtered_events['year'].isin([2018, 2023])]

        # Aggregate events
        events_agg = events_filtered.groupby(['boundary_i', 'year']).size().unstack(fill_value=0).reset_index()
        events_agg.columns = ['boundary_i', 'events_2018', 'events_2023']

        # Merge with shapefile
        filtered_data = ca_gdf.merge(events_agg, on='boundary_i', how='left')
        filtered_data['events_2018'] = filtered_data['events_2018'].fillna(0)
        filtered_data['events_2023'] = filtered_data['events_2023'].fillna(0)

        # Calculate percent change for each region
        filtered_data['percent_change'] = (
            (filtered_data['events_2023'] - filtered_data['events_2018']) /
            filtered_data['events_2018'].replace(0, np.nan)
        ) * 100
        filtered_data['percent_change'] = filtered_data['percent_change'].replace([np.inf, -np.inf], np.nan)
        filtered_data['percent_change'] = filtered_data['percent_change'].fillna(0).clip(lower=-500, upper=700)

        # Calculate overall statistics
        total_events_2018 = filtered_data['events_2018'].sum()
        total_events_2023 = filtered_data['events_2023'].sum()
        avg_percent_change = filtered_data['percent_change'].mean()

        # Calculate total percent change
        if total_events_2018 > 0:  # Avoid division by zero
            total_percent_change = ((total_events_2023 - total_events_2018) / total_events_2018) * 100
        else:
            total_percent_change = 0

        # Format and align the text
        stats_text = (
            f"Summary Statistics:\n"
            f"-------------------\n"
            f"Total Events in 2018   : {total_events_2018:.1f}\n"
            f"Total Events in 2023   : {total_events_2023:.1f}\n"
            f"Average Percent Change : {avg_percent_change:.2f}%\n"
            f"Total Percent Change   : {total_percent_change:.2f}%\n"
        )
        return stats_text

# Step 4: Launch the app
app = App(app_ui, server)


### in terminal: 'shiny run app.py'
### 'ctrl + c' to close



import os
import pandas as pd
from glob import glob
import numpy as np
import matplotlib.pyplot as plt


def dms_string_to_decimal(dms_string):
    if pd.isna(dms_string):
        return np.nan  # Return NaN if input is NaN

    degrees = float(dms_string[:2])  # Extract degrees part
    minutes = float(dms_string[2:-1])  # Extract minutes and seconds
    direction = dms_string[-1]  # Extract direction (N, S, E, W)

    decimal_degrees = degrees + (minutes / 60.0)
    if direction in ['S', 'W']:
        decimal_degrees = -decimal_degrees  # Ensure negative for south and west directions

    return decimal_degrees


def create_dataframe(folder, output_file):

    csv_files = glob(os.path.join(folder, "*.csv"))

    dataframes = []

    for file in csv_files:
        # Filename is column name without the extension
        column_name = os.path.splitext(os.path.basename(file))[0]
        # Read the CSV file into a dataframe
        df = pd.read_csv(file, header=None, names=['timestamp', column_name])
        # Append the dataframe to the list
        dataframes.append(df)

    # Merge all dataframes on the 'timestamp' column using an outer join to keep all timestamps
    merged_df = dataframes[0]
    for df in dataframes[1:]:
        merged_df = pd.merge(merged_df, df, on='timestamp', how='outer')

    # Sort the dataframe by the 'timestamp' column
    merged_df = merged_df.sort_values(by='timestamp')
    # Save the concatenated dataframe to the specified CSV file
    merged_df.to_csv(output_file, index=False)

    print(f"Concatenated CSV file saved to {output_file}")


def clr_datetime_to_unix_time(clr_datetime):
    # Ticks between CLR DateTime epoch (0001-01-01) and Unix epoch (1970-01-01)
    CLR_UNIX_EPOCH_DIFF_TICKS = 621355968000000000  # 1 tick = 100 nanoseconds

    # Convert the CLR DateTime integer to Unix timestamp
    if pd.isna(clr_datetime):
        return pd.NaT  # Return NaT (Not a Time) for NaN values
    else:
        unix_timestamp = (clr_datetime - CLR_UNIX_EPOCH_DIFF_TICKS) // 10000000
        return pd.Timestamp(unix_timestamp, unit='s')  # Convert Unix timestamp to pandas Timestamp


def process_dataframe(folder, filename, pred_column):

    df = pd.read_csv(filename)

    # Check that the DataFrame does not miss any columns
    num_of_columns = len(glob(os.path.join(folder, "*.csv")))
    assert len(df.columns) == num_of_columns + 1  # folder-files plus Timestamp

    first_valid_index = df[pred_column].first_valid_index()

    if first_valid_index is not None:
        # Slice the DataFrame to keep rows from the first valid index onwards
        df = df.loc[first_valid_index:]
        df.reset_index(drop=True, inplace=True)  # Reset index after slicing

    last_valid_index = df[pred_column].last_valid_index()

    if last_valid_index is not None:
        # Slice the DataFrame to keep rows up to and including the last valid index
        df = df.loc[:last_valid_index]
        df.reset_index(drop=True, inplace=True)  # Reset index after slicing

    # Translate the timestamps into a more readable and processable format (pandas DateTime)
    df['datetime'] = df['timestamp'].apply(clr_datetime_to_unix_time)
    df['datetime'] = pd.to_datetime(df['datetime'])

    df = df.drop(columns=['timestamp'])

    df.to_csv(filename, index=False)


def stats_dataframe(df, aggr=True):

    # Calculate percentage of NaN values for each column
    nan_percentage = df.isna().mean() * 100
    print("Percentage of NaN values for each column:")
    print(nan_percentage)

    if aggr:
        # Select non-string columns
        non_string_columns = df.select_dtypes(exclude=['object'])

        # Calculate mean and standard deviation
        mean_values = non_string_columns.mean()
        std_values = non_string_columns.std()

        # Combine mean and std values into a single DataFrame
        mean_std_df = pd.concat([mean_values, std_values], axis=1)
        mean_std_df.columns = ['Mean', 'Std']

        # Print mean and std values side by side
        print("Mean and Standard Deviation Values:")
        print(mean_std_df)


def plot_values(df, plot_dir):

    # Directory to save plots
    os.makedirs(plot_dir, exist_ok=True)

    # List of all columns excluding the target column
    columns = [col for col in df.columns if col != 'fuelVolumeFlowRate' and col != 'datetime']

    # Plotting
    for col in columns:
        # Filter out rows where either the current column or 'fuelVolumeFlowRate' is NaN
        filtered_df = df[[col, 'fuelVolumeFlowRate']].dropna()

        print(f'Column:{col}, filtered df shape: {filtered_df.shape}')

        # Create a scatter plot
        plt.figure()
        plt.scatter(filtered_df[col], filtered_df['fuelVolumeFlowRate'])
        plt.xlabel(col)
        plt.ylabel('fuelVolumeFlowRate')
        plt.title(f'Scatter plot of {col} vs fuelVolumeFlowRate')

        # Save the plot as an image file
        plot_filename = os.path.join(plot_dir, f'{col}_vs_fuelVolumeFlowRate.png')
        plt.savefig(plot_filename)

        # Close the plot to free up memory
        plt.close('all')


if not os.path.exists("data"):
    os.makedirs("data")

data_folder = os.path.abspath('raw_data')
out_csv = "./data/final.csv"

create_dataframe(folder=data_folder, output_file=out_csv)
process_dataframe(folder=data_folder, filename=out_csv, pred_column='fuelVolumeFlowRate')

aggr_data = True
aggregation_vals = ['3min', '10min']
plot, show_stats = False, False

if aggr_data:
    for aggregation in aggregation_vals:
        df = pd.read_csv(out_csv)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)

        # Convert latitude and longitude to numerical values
        df['latitude'] = df['latitude'].apply(dms_string_to_decimal)
        df['longitude'] = df['longitude'].apply(dms_string_to_decimal)

        if show_stats:
            print("Statistics for non-aggregated raw_data")
            stats_dataframe(df=df)

        print(f"Created {aggregation}ute aggregated data")
        # Resample to intervals and aggregate
        df_resampled = df.resample(aggregation).agg(['mean', 'std'])

        if show_stats:
            print(f"Statistics {aggregation}ute aggregated data")
            stats_dataframe(df=df_resampled, aggr=False)

        if not os.path.exists("data_plots"):
            os.makedirs("data_plots")

        if plot:
            plot_values(df=df, plot_dir=f'./data_plots/plots_{aggregation}_aggr')

        df_resampled = df_resampled.reset_index()
        df_resampled.to_csv(f"./data/aggr_{aggregation}.csv", index=False)

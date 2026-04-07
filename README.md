# XDF to CSV Converter GUI

Simple desktop GUI tool to:

1. Load an `.xdf` file
2. Export selected XDF streams into one combined `.csv`
3. In one section, choose either all data or a marker window, then create X-Y plots

## Requirements

- Python 3.9+ recommended
- Dependencies listed in `requirements.txt`

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
python xdf_csv_plot_gui.py
```

## How to Use

1. In section **Load XDF and Export CSV**:
   - Click `Browse` and choose an `.xdf` file.
   - Choose an output directory.
   - Click `Load Streams`.
   - Select one or more streams from the list.
   - Click `Export Combined CSV`.
   - The app creates one file named `<xdf_name>_combined.csv`.
2. In section **Select Data and Plot**:
   - Pick a CSV file (the combined export, or any compatible CSV).
   - Click `Load CSV Columns`.
   - Choose `Data scope`:
     - `All data`, or
     - `Between event markers`
   - Marker controls (`Marker column`, `Start marker`, `End marker`) are shown only when `Between event markers` is selected.
   - Choose `X column` and `Y column`.
   - Click `Plot X-Y` for line plot or `Scatter` for scatter plot.
   - Optional: click `Export Selected Scope CSV` to save either all data or the selected marker window.

## Notes

- Combined CSV includes one shared `timestamp` column.
- Combined CSV also includes `time_sec`, where first valid timestamp is `0.0` and values increase in seconds.
- Stream columns are prefixed as `streamIndex_streamName_columnName` to avoid name collisions.
- Plotting expects numeric X and Y values; non-numeric values are ignored.

import os
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyxdf


class XDFCSVPlotGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("XDF -> CSV Converter and Plotter")
        self.root.geometry("980x700")

        self.xdf_file = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.selected_stream_indices = []
        self.streams = []
        self.csv_file = tk.StringVar()
        self.x_column = tk.StringVar()
        self.y_column = tk.StringVar()
        self.marker_column = tk.StringVar()
        self.start_marker = tk.StringVar()
        self.end_marker = tk.StringVar()
        self.data_scope = tk.StringVar(value="all")
        self.status_text = tk.StringVar(value="Ready.")
        self.current_df = None
        self.filtered_df = None

        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        v_scroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        main = ttk.Frame(self.canvas, padding=12)
        self.canvas_window = self.canvas.create_window((0, 0), window=main, anchor="nw")

        def _on_frame_configure(_event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def _on_canvas_configure(event):
            self.canvas.itemconfigure(self.canvas_window, width=event.width)

        main.bind("<Configure>", _on_frame_configure)
        self.canvas.bind("<Configure>", _on_canvas_configure)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        title = ttk.Label(
            main,
            text="XDF to CSV Converter + CSV X-Y Plotter",
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(anchor="w", pady=(0, 10))

        xdf_frame = ttk.LabelFrame(main, text="1) Load XDF and Export CSV", padding=10)
        xdf_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(xdf_frame, text="XDF file:").grid(row=0, column=0, sticky="w")
        ttk.Entry(xdf_frame, textvariable=self.xdf_file, width=90).grid(
            row=0, column=1, padx=6, pady=4, sticky="we"
        )
        ttk.Button(xdf_frame, text="Browse", command=self.pick_xdf_file).grid(
            row=0, column=2, padx=4
        )

        ttk.Label(xdf_frame, text="Output folder:").grid(row=1, column=0, sticky="w")
        ttk.Entry(xdf_frame, textvariable=self.output_dir, width=90).grid(
            row=1, column=1, padx=6, pady=4, sticky="we"
        )
        ttk.Button(xdf_frame, text="Browse", command=self.pick_output_dir).grid(
            row=1, column=2, padx=4
        )

        ttk.Button(
            xdf_frame, text="Load Streams", command=self.load_xdf_streams
        ).grid(row=2, column=1, sticky="w", pady=8)

        streams_wrap = ttk.Frame(xdf_frame)
        streams_wrap.grid(row=3, column=0, columnspan=3, sticky="nsew")

        ttk.Label(streams_wrap, text="Select streams to export as CSV:").pack(anchor="w")
        self.stream_listbox = tk.Listbox(
            streams_wrap, selectmode=tk.EXTENDED, height=10, exportselection=False
        )
        self.stream_listbox.pack(fill=tk.X, pady=(4, 6))

        ttk.Button(
            xdf_frame, text="Export Combined CSV", command=self.export_selected_streams
        ).grid(row=4, column=1, sticky="w", pady=(2, 0))

        xdf_frame.columnconfigure(1, weight=1)

        plot_frame = ttk.LabelFrame(main, text="2) Select Data and Plot", padding=10)
        plot_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(plot_frame, text="CSV file:").grid(row=0, column=0, sticky="w")
        ttk.Entry(plot_frame, textvariable=self.csv_file, width=90).grid(
            row=0, column=1, padx=6, pady=4, sticky="we"
        )
        ttk.Button(plot_frame, text="Browse", command=self.pick_csv_file).grid(
            row=0, column=2, padx=4
        )
        ttk.Button(plot_frame, text="Load CSV Columns", command=self.load_csv_columns).grid(
            row=1, column=1, sticky="w", pady=6
        )

        ttk.Label(plot_frame, text="Data scope:").grid(row=2, column=0, sticky="w")
        scope_row = ttk.Frame(plot_frame)
        scope_row.grid(row=2, column=1, sticky="w", padx=6, pady=4)
        ttk.Radiobutton(scope_row, text="All data", value="all", variable=self.data_scope).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        ttk.Radiobutton(
            scope_row, text="Between event markers", value="markers", variable=self.data_scope
        ).pack(side=tk.LEFT)

        self.marker_label = ttk.Label(plot_frame, text="Marker column:")
        self.marker_label.grid(row=3, column=0, sticky="w")
        self.marker_combo = ttk.Combobox(plot_frame, textvariable=self.marker_column, state="readonly")
        self.marker_combo.grid(row=3, column=1, sticky="we", padx=6, pady=4)
        self.marker_combo.bind("<<ComboboxSelected>>", lambda _e: self.update_marker_values())

        self.start_marker_label = ttk.Label(plot_frame, text="Start marker:")
        self.start_marker_label.grid(row=4, column=0, sticky="w")
        self.start_marker_combo = ttk.Combobox(
            plot_frame, textvariable=self.start_marker, state="readonly"
        )
        self.start_marker_combo.grid(row=4, column=1, sticky="we", padx=6, pady=4)

        self.end_marker_label = ttk.Label(plot_frame, text="End marker:")
        self.end_marker_label.grid(row=5, column=0, sticky="w")
        self.end_marker_combo = ttk.Combobox(
            plot_frame, textvariable=self.end_marker, state="readonly"
        )
        self.end_marker_combo.grid(row=5, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(plot_frame, text="X column:").grid(row=6, column=0, sticky="w")
        self.x_combo = ttk.Combobox(plot_frame, textvariable=self.x_column, state="readonly")
        self.x_combo.grid(row=6, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(plot_frame, text="Y column:").grid(row=7, column=0, sticky="w")
        self.y_combo = ttk.Combobox(plot_frame, textvariable=self.y_column, state="readonly")
        self.y_combo.grid(row=7, column=1, sticky="we", padx=6, pady=4)

        button_row = ttk.Frame(plot_frame)
        button_row.grid(row=8, column=1, sticky="w", pady=8)
        ttk.Button(button_row, text="Plot X-Y", command=self.plot_xy).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="Scatter", command=lambda: self.plot_xy(style="scatter")).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(
            button_row, text="Export Selected Scope CSV", command=self.export_filtered_csv
        ).pack(side=tk.LEFT, padx=(0, 8))
        plot_frame.columnconfigure(1, weight=1)
        self.data_scope.trace_add("write", lambda *_args: self.update_scope_visibility())
        self.update_scope_visibility()

        status = ttk.Label(main, textvariable=self.status_text, foreground="#1f4f8a")
        status.pack(anchor="w")

        hint = ttk.Label(
            main,
            text="Dependencies: pip install pyxdf pandas matplotlib",
            foreground="#555555",
        )
        hint.pack(anchor="w", pady=(8, 0))

    def _on_mousewheel(self, event):
        if self.root.focus_displayof() is None:
            return
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_status(self, text: str):
        self.status_text.set(text)
        self.root.update_idletasks()

    def update_scope_visibility(self):
        show_markers = self.data_scope.get() == "markers"
        marker_widgets = [
            self.marker_label,
            self.marker_combo,
            self.start_marker_label,
            self.start_marker_combo,
            self.end_marker_label,
            self.end_marker_combo,
        ]
        if show_markers:
            self.marker_label.grid(row=3, column=0, sticky="w")
            self.marker_combo.grid(row=3, column=1, sticky="we", padx=6, pady=4)
            self.start_marker_label.grid(row=4, column=0, sticky="w")
            self.start_marker_combo.grid(row=4, column=1, sticky="we", padx=6, pady=4)
            self.end_marker_label.grid(row=5, column=0, sticky="w")
            self.end_marker_combo.grid(row=5, column=1, sticky="we", padx=6, pady=4)
        else:
            for widget in marker_widgets:
                widget.grid_remove()

    def pick_xdf_file(self):
        path = filedialog.askopenfilename(
            title="Select XDF file", filetypes=[("XDF files", "*.xdf"), ("All files", "*.*")]
        )
        if path:
            self.xdf_file.set(path)
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(path))

    def pick_output_dir(self):
        path = filedialog.askdirectory(title="Select output directory")
        if path:
            self.output_dir.set(path)

    def pick_csv_file(self):
        path = filedialog.askopenfilename(
            title="Select CSV file", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.csv_file.set(path)

    @staticmethod
    def _stream_name(stream: dict, index: int) -> str:
        info = stream.get("info", {})
        name = (info.get("name") or ["unknown"])[0]
        stype = (info.get("type") or ["unknown"])[0]
        chans = (info.get("channel_count") or ["?"])[0]
        srate = (info.get("nominal_srate") or ["?"])[0]
        return f"[{index}] name={name}, type={stype}, channels={chans}, srate={srate}"

    @staticmethod
    def _extract_channel_labels(stream: dict, default_count: int) -> list[str]:
        labels = []
        try:
            desc = stream["info"]["desc"][0]
            channels = desc.get("channels", [{}])[0].get("channel", [])
            for i, channel in enumerate(channels):
                label = channel.get("label", [f"ch_{i}"])[0]
                labels.append(str(label))
        except Exception:
            pass

        if len(labels) < default_count:
            labels.extend([f"ch_{i}" for i in range(len(labels), default_count)])
        return labels[:default_count]

    def load_xdf_streams(self):
        path = self.xdf_file.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror("Error", "Please select a valid XDF file.")
            return

        self.set_status("Loading XDF streams...")
        try:
            streams, _ = pyxdf.load_xdf(path)
            self.streams = streams
            self.stream_listbox.delete(0, tk.END)
            for idx, stream in enumerate(streams):
                self.stream_listbox.insert(tk.END, self._stream_name(stream, idx))
            self.set_status(f"Loaded {len(streams)} stream(s).")
        except Exception as e:
            self.set_status("Failed to load XDF.")
            messagebox.showerror("Error", f"Could not load XDF:\n{e}")

    @staticmethod
    def _normalize_cell(value):
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="replace")
            except Exception:
                return str(value)
        if isinstance(value, (list, tuple, np.ndarray)):
            flat = np.asarray(value).reshape(-1)
            if flat.size == 1:
                return XDFCSVPlotGUI._normalize_cell(flat[0])
            return "|".join(str(XDFCSVPlotGUI._normalize_cell(v)) for v in flat.tolist())
        return value

    def _stream_to_dataframe(self, stream: dict) -> pd.DataFrame:
        timestamps = np.asarray(stream.get("time_stamps", []), dtype=float)
        series = stream.get("time_series", [])

        if len(series) == 0:
            return pd.DataFrame({"timestamp": timestamps})

        series_arr = np.asarray(series, dtype=object)
        if series_arr.ndim == 1:
            normalized = [self._normalize_cell(v) for v in series_arr.tolist()]
            data = pd.DataFrame({"value": normalized})
        else:
            channel_count = series_arr.shape[1]
            col_names = self._extract_channel_labels(stream, channel_count)
            data = pd.DataFrame(series_arr.tolist(), columns=col_names)
            for col in data.columns:
                data[col] = data[col].map(self._normalize_cell)

        data.insert(0, "timestamp", timestamps)
        return data

    @staticmethod
    def _sanitize_name(value: str) -> str:
        return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(value))

    @staticmethod
    def _ensure_time_sec_column(df: pd.DataFrame) -> pd.DataFrame:
        if "time_sec" in df.columns:
            return df
        if "timestamp" not in df.columns:
            return df
        ts = pd.to_numeric(df["timestamp"], errors="coerce")
        first_valid = ts.dropna()
        if first_valid.empty:
            return df
        df["time_sec"] = ts - first_valid.iloc[0]
        return df

    def export_selected_streams(self):
        out_dir = self.output_dir.get().strip()
        if not out_dir:
            messagebox.showerror("Error", "Please choose an output directory.")
            return
        os.makedirs(out_dir, exist_ok=True)

        selected = self.stream_listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one stream.")
            return

        self.set_status("Exporting combined CSV...")
        errors = []
        merged_df = None
        selected_names = []
        for idx in selected:
            try:
                stream = self.streams[idx]
                df = self._stream_to_dataframe(stream)
                stream_name = (stream.get("info", {}).get("name") or [f"stream_{idx}"])[0]
                safe_name = self._sanitize_name(stream_name)
                selected_names.append(f"{idx:02d}_{safe_name}")

                rename_map = {
                    col: f"{idx:02d}_{safe_name}_{self._sanitize_name(col)}"
                    for col in df.columns
                    if col != "timestamp"
                }
                df = df.rename(columns=rename_map)
                df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
                if merged_df is None:
                    merged_df = df
                else:
                    merged_df = pd.merge(
                        merged_df,
                        df,
                        on="timestamp",
                        how="outer",
                    )
            except Exception as e:
                errors.append(f"Stream {idx}: {e}")

        if merged_df is not None:
            merged_df = merged_df.sort_values("timestamp").reset_index(drop=True)
            merged_df = self._ensure_time_sec_column(merged_df)
            stem = os.path.splitext(os.path.basename(self.xdf_file.get().strip()))[0]
            out_path = os.path.join(out_dir, f"{self._sanitize_name(stem)}_combined.csv")
            merged_df.to_csv(out_path, index=False)

            self.csv_file.set(out_path)
            self.set_status("Combined CSV exported.")
            msg = "Combined CSV export finished.\n\nSaved file:\n" + out_path
            msg += "\n\nIncluded streams:\n" + "\n".join(selected_names)
            if errors:
                msg += "\n\nSome streams failed:\n" + "\n".join(errors)
            messagebox.showinfo("Export Complete", msg)
        else:
            self.set_status("No file exported.")
            messagebox.showerror("Export Failed", "\n".join(errors) if errors else "Unknown error.")

    def load_csv_columns(self):
        path = self.csv_file.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror("Error", "Please select a valid CSV file.")
            return

        self.set_status("Reading CSV columns...")
        try:
            self.current_df = pd.read_csv(path)
            self.current_df = self._ensure_time_sec_column(self.current_df)
            df = self.current_df
            if df.empty:
                messagebox.showwarning("Empty CSV", "The selected CSV appears to be empty.")
                return

            columns = list(df.columns)
            numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
            self.x_combo["values"] = columns
            self.y_combo["values"] = numeric_cols if numeric_cols else columns

            if "time_sec" in columns:
                self.x_column.set("time_sec")
            elif "timestamp" in columns:
                self.x_column.set("timestamp")
            elif columns:
                self.x_column.set(columns[0])

            if numeric_cols:
                preferred = [c for c in numeric_cols if c != self.x_column.get()]
                self.y_column.set(preferred[0] if preferred else numeric_cols[0])
            elif len(columns) > 1:
                self.y_column.set(columns[1])
            elif columns:
                self.y_column.set(columns[0])

            marker_candidates = [
                c for c in columns if "marker" in c.lower() or "event" in c.lower()
            ]
            self.marker_combo["values"] = marker_candidates
            if marker_candidates:
                self.marker_column.set(marker_candidates[0])
                self.update_marker_values()
            else:
                self.marker_column.set("")
                self.start_marker_combo["values"] = []
                self.end_marker_combo["values"] = []
                self.start_marker.set("")
                self.end_marker.set("")

            self.filtered_df = None
            self.set_status(f"Loaded {len(columns)} columns from CSV.")
        except Exception as e:
            self.set_status("Failed to read CSV.")
            messagebox.showerror("Error", f"Could not read CSV:\n{e}")

    def update_marker_values(self):
        if self.current_df is None:
            return
        marker_col = self.marker_column.get().strip()
        if not marker_col or marker_col not in self.current_df.columns:
            return

        series = self.current_df[marker_col]
        non_empty = series.dropna().astype(str)
        non_empty = non_empty[non_empty.str.strip() != ""]
        unique_values = list(dict.fromkeys(non_empty.tolist()))
        self.start_marker_combo["values"] = unique_values
        self.end_marker_combo["values"] = unique_values

        if unique_values and not self.start_marker.get():
            self.start_marker.set(unique_values[0])
        if unique_values and not self.end_marker.get():
            self.end_marker.set(unique_values[min(1, len(unique_values) - 1)])

    def apply_marker_window(self, show_popup: bool = True):
        if self.current_df is None:
            messagebox.showerror("Error", "Please load a CSV first.")
            return
        marker_col = self.marker_column.get().strip()
        start_marker = self.start_marker.get().strip()
        end_marker = self.end_marker.get().strip()
        if marker_col not in self.current_df.columns:
            messagebox.showerror("Error", "Please select a valid marker column.")
            return
        if not start_marker or not end_marker:
            messagebox.showerror("Error", "Please select both start and end markers.")
            return

        marker_series = self.current_df[marker_col].fillna("").astype(str).str.strip()
        start_hits = self.current_df.index[marker_series == start_marker].tolist()
        if not start_hits:
            messagebox.showerror("Error", f"Start marker not found: {start_marker}")
            return

        start_idx = start_hits[0]
        end_hits = self.current_df.index[(marker_series == end_marker) & (self.current_df.index > start_idx)].tolist()
        if not end_hits:
            messagebox.showerror(
                "Error",
                f"No end marker '{end_marker}' found after start marker '{start_marker}'.",
            )
            return

        end_idx = end_hits[0]
        self.filtered_df = self.current_df.loc[start_idx:end_idx].copy()
        self.set_status(
            f"Filtered rows {start_idx}..{end_idx} ({len(self.filtered_df)} rows) using markers."
        )
        if show_popup:
            messagebox.showinfo(
                "Marker Window Applied",
                f"Start marker '{start_marker}' at row {start_idx}\n"
                f"End marker '{end_marker}' at row {end_idx}\n"
                f"Filtered rows: {len(self.filtered_df)}",
            )

    def _get_active_dataframe(self):
        if self.current_df is None:
            raise ValueError("Please load a CSV first.")
        if self.data_scope.get() == "all":
            return self.current_df
        self.apply_marker_window(show_popup=False)
        if self.filtered_df is None or self.filtered_df.empty:
            raise ValueError("No data found in selected marker window.")
        return self.filtered_df

    def export_filtered_csv(self):
        try:
            df_to_export = self._get_active_dataframe()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        out_dir = self.output_dir.get().strip()
        if not out_dir:
            csv_path = self.csv_file.get().strip()
            out_dir = os.path.dirname(csv_path) if csv_path else ""
        if not out_dir:
            messagebox.showerror("Error", "Please choose an output directory.")
            return
        os.makedirs(out_dir, exist_ok=True)

        stem = os.path.splitext(os.path.basename(self.csv_file.get().strip() or "combined"))[0]
        if self.data_scope.get() == "markers":
            start = self._sanitize_name(self.start_marker.get().strip() or "start")
            end = self._sanitize_name(self.end_marker.get().strip() or "end")
            out_name = f"{stem}_{start}_to_{end}.csv"
        else:
            out_name = f"{stem}_all_data.csv"
        out_path = os.path.join(out_dir, out_name)
        df_to_export.to_csv(out_path, index=False)
        self.set_status(f"Scope CSV exported: {out_path}")
        messagebox.showinfo("Export Complete", f"Saved CSV:\n{out_path}")

    def plot_xy(self, style: str = "line"):
        path = self.csv_file.get().strip()
        x_col = self.x_column.get().strip()
        y_col = self.y_column.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror("Error", "Please select a valid CSV file.")
            return
        if not x_col or not y_col:
            messagebox.showerror("Error", "Please select both X and Y columns.")
            return

        self.set_status(f"Plotting {y_col} vs {x_col}...")
        try:
            if self.current_df is None:
                self.current_df = pd.read_csv(path)
            df = self._get_active_dataframe()
            if x_col not in df.columns or y_col not in df.columns:
                messagebox.showerror("Error", "Selected columns were not found in the CSV.")
                return

            x = pd.to_numeric(df[x_col], errors="coerce")
            y = pd.to_numeric(df[y_col], errors="coerce")
            mask = x.notna() & y.notna()
            x = x[mask]
            y = y[mask]

            if len(x) == 0:
                messagebox.showwarning("No Data", "No numeric X/Y data points available for plotting.")
                return

            plt.figure(figsize=(10, 5))
            if style == "scatter":
                plt.scatter(x, y, s=12, alpha=0.75)
            else:
                plt.plot(x, y, linewidth=1.2)
            plt.xlabel(x_col)
            plt.ylabel(y_col)
            plt.title(f"{os.path.basename(path)}: {y_col} vs {x_col}")
            plt.grid(True, alpha=0.35)
            plt.tight_layout()
            plt.show()
            self.set_status("Plot displayed.")
        except Exception as e:
            self.set_status("Plot failed.")
            messagebox.showerror("Error", f"Failed to plot data:\n{e}\n\n{traceback.format_exc()}")


def main():
    root = tk.Tk()
    app = XDFCSVPlotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

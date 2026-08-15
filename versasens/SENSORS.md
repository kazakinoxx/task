# Sensors

## Location

The different sensors can be found in folder [src/versa/sensors](src/versa/sensors/).

## Create a new sensor

This section will describe how to implement a new sensor.

### 1. Create the sensor class

Create a new file with a `dataclass` extending the `Sensor` class.

It needs to contain the different lists needed to store the data of the sensor.
The list of indices (`idx_list`), of timestamps (`time_list`), of plots (`plots`) and
the last index `last_idx` are already handled by the `Sensor` class and would usually
already be handled by the super-class.

The lists need to be instantiated.

For example:

```python
import dataclasses
from dataclasses import dataclass
from src.versa.sensor import Sensor

@dataclass
class MLX(Sensor):
    # Creates empty lists as default values
    temp_a: list[float] = field(default_factory=list)
    """List of ambient temperatures in Celsius."""

    temp_o: list[float] = field(default_factory=list)
    """List of object temperatures in Celsius."""
    ...
```

### 2. Implement functions

There are multiple functions that are needed for implementing the parsing, saving, and
plotting of the sensor's data.

Some functions are required to be implemented, and some can be overridden in special
cases (e.g. when needing to create an additional audio file when saving data to the
database).

#### Required functions

The following functions need to be implemented for each sensor. Other functions, such
as saving CSV files when storing data in the database are already implemented and, in
most cases, don't need to be modified.

##### headers

Returns a list of headers related to this sensor.
For example:

```python
@dataclass
class MLX(Sensor):
    @staticmethod
    @override
    def headers() -> list[SensorHeader]:
        return [b"\xbb\xbb"]

    ...
```

##### clear

This function is needed to clear (empty) the stored data. This is used for performance
reasons, for instance, when plotting data.

For example:

```python
@dataclass
class MLX(Sensor):
    @override
    def clear(self) -> None:
        # Need to call the super-class' clear function
        super().clear()

        # Manually clear the stored lists
        self.temp_a.clear()
        self.temp_o.clear()

    ...
```

##### parse_file

This function gets as arguments a reference to the raw file, and the length of the
packet. At this point, the header, the timestamp and the length have already been read
(c.f. `SensorGroup.add_data_single_read`).
This function only needs to handle reading the actual data and storing it in the class.

For example:

```python
@dataclass
class MLX(Sensor):
    @override
    def parse_file(self, raw_data: RawData, length: int) -> None:
        ambient_t_bytes = raw_data.read(4)
        ambient_t = struct.unpack("f", ambient_t_bytes)[0]
        self.temp_a.append(ambient_t)

        object_t_bytes = raw_data.read(4)
        object_t = struct.unpack("f", object_t_bytes)[0]
        self.temp_o.append(object_t)

    ...
```

##### plot_graphics

This function creates the plots, puts the stored data in the plots, and returns the
resulting curves.

For example:

```python
@dataclass
class MLX(Sensor):
    @override
    def plot_graphics(self, graphics: GraphicsLayoutWidget) -> dict[str, PlotDataItem]:
        # Create a dict of plot name to the created curve
        curves: dict[str, PlotDataItem] = {}

        # Create a new plot with a given title
        plot: PlotItem = graphics.ci.addPlot(
            title="MLX90632 Temperature Measurement",
        )
        # Set axis labels
        plot.setLabel("bottom", "Time (s)")
        plot.setLabel("left", "Temperature (°C)")
        # Add a legend to the plot
        plot.addLegend()
        # Show a grid in the plot
        plot.showGrid(x=True, y=True)

        # Create curves in the plot for the object temperature and for the ambient
        # temperature
        # In this case, two curves are written in the same plot
        curves["temp_o"] = plot.plot(name="Object")
        curves["temp_a"] = plot.plot(name="Ambient")

        # Store the plots
        self.plots = [plot]

        # Call set_plot_data to put the data in the plots
        self.set_plot_data(curves)

        # Return the created curves
        return curves

    ...
```

##### set_plot_data

This function, in turn, will put the stored data into the plots.

For example:

```python
@dataclass
class MLX(Sensor):
    @override
    def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:
        # Convert timestamps to seconds
        time_list_secs = np.array(self.time_list) / 1000.0

        # Set curves data
        curves["temp_o"].setData(
            x=time_list_secs,
            y=self.temp_o,
            # The name of the curve
            name="Object",
            # The color of the curve. Useful when plotting multiple curves in the same
            # plot
            pen=COLORS[0],
        )
        curves["temp_a"].setData(
            x=time_list_secs,
            y=self.temp_a,
            # The name of the curve
            name="Ambient",
            # The color of the curve. Useful when plotting multiple curves in the same
            # plot
            pen=COLORS[1],
        )

    ...
```

#### Optional functions

These functions are already implemented in the super-class but, in some cases, it may
be necessary to change the default behavior.

##### name

This function returns the full name of the sensor. By default, it uses the name of the
class.

In may need to be overridden if the name of the class is not the full name of the
sensor.

For example:

```python
@dataclass
class MLX(Sensor):
    @classmethod
    @override
    def name(cls) -> str:
        return "MLX90632"

    ...
```

##### attr_name

This function returns the shortened lower-case name of the sensor. By default, it
returns the name of the sensor in lower case.

In may need to be overridden if, for instance, the full name is too long.

For example:

```python
@dataclass
class MLX(Sensor):
    @classmethod
    @override
    def attr_name(cls) -> str:
        return "mlx"

    ...
```

##### _delete_stale_data

This function, used for performance reasons during plotting, deletes old data stored in
the sensor, so only the last few seconds are kept. This prevents hours of parsed data
to be stored in memory during long sessions when plotting.

The function may need to be overridden if, for instance, multiple time lists are being
stored. By default, all lists are trimmed, so most cases wouldn't need to override the
super-class' function.

For example, the MAX86178 sensor has separate time lists for each sub-sensor (4 PPGs,
ECG, BIOZ):

```python
@dataclass
class MAX86178(Sensor):
    @override
    def _delete_stale_data(self) -> bool:
        """Remove data older than the displayed window to reduce memory usage."""
        # Exit if the sensor has no data yet
        if len(self.time_list) == 0:
            return False

        time_data_lst: list[tuple[list[int], str]] = [
            (self.time_list_ppg0, "ppg0_list"),
            (self.time_list_ppg1, "ppg1_list"),
            (self.time_list_ppg2, "ppg2_list"),
            (self.time_list_ppg3, "ppg3_list"),
            (self.time_list_bioz_86, "bioz_list_86"),
            (self.time_list_ecg_86, "ecg_list_86"),
        ]

        for time_list, field_name in time_data_lst:
            last_time_ms = time_list[-1]
            cutoff_time_ms = last_time_ms - ((PLOT_SHOW_LAST_SECONDS + 1) * 1000)

            # Find first visible index
            start_idx = bisect.bisect_left(time_list, cutoff_time_ms)

            # If no trimming needed
            if start_idx <= 0:
                continue

            # Trim list
            value = getattr(self, field_name)

            # Only trim lists of scalars
            if isinstance(value, list):
                del value[:start_idx]

        # Normal list trimming
        last_time_ms = self.time_list[-1]
        cutoff_time_ms = last_time_ms - ((PLOT_SHOW_LAST_SECONDS + 1) * 1000)

        # Find first visible index
        start_idx = bisect.bisect_left(self.time_list, cutoff_time_ms)

        # If no trimming needed
        if start_idx <= 0:
            return False

        # Update last_idx
        self.last_idx = self.idx_list[-1]
        return True

    ...
```

##### to_dict

This function puts the stored sensor data in a dictionary of values. This dictionary
will then be used to create the CSV files.

In some cases, the dictionary needs to be manually created. For instance, T5838's
microphone data is stored in a list of bytes. However, the bytes need first to be
converted in hexadecimal strings to stored them in CSV files.

Implementing this function in the subclass requires the `_from_dict` function to also
be implemented.

For example:

```python
@dataclass
class T5838(Sensor):
    pcm_data: list[bytes] = field(default_factory=list)

    @override
    def to_dict(self) -> dict[str, Any]:
        return {
            "last_idx": self.last_idx,
            # Convert the bytes to hexadecimal strings
            "pcm_data": [b.hex() for b in self.pcm_data],
            "time_list": self.time_list,
            "idx_list": self.idx_list,
        }

    ...
```

##### _from_dict

This function creates a new sensor from a dictionary of values. This dictionary contains
the data directly read from a CSV file.

It needs to be implemented if some changes were made to `to_dict`'s default behavior.

For example:

```python
@dataclass
class T5838(Sensor):
    pcm_data: list[bytes] = field(default_factory=list)

    @classmethod
    @override
    def _from_dict(cls, dict_var: dict) -> Self:
        # Create a new blank sensor instance
        res = cls()

        res.last_idx = dict_var["last_idx"]
        # Convert the hexadecimal strings to bytes
        res.pcm_data = [bytes.fromhex(h) for h in dict_var["pcm_data"]]
        res.time_list = dict_var["time_list"]
        res.idx_list = dict_var["idx_list"]

        return res
```

##### _write_csvs

This function writes the sensor's data into the given list of CSV files.

It needs to be implemented if the stored data can't be written automatically into
a single CSV file. This happens for instance in the MAX86178 sensor, as it contains
different time and data lists for each PPG, for the ECG and for the BIOZ sensor.

In this function, `file_paths` correspond to the filenames given by the `_csv_filenames`
function (which needs to be overridden when writing multiple files), `write_behaviour`
indicates whether the data needs to be appended if the files already exist or if the
file needs to be overwritten, and `dry_run` indicates if the writes need to be simulated
or not.

For example:

```python
@dataclass
class MAX86178(Sensor):
    @override
    def _write_csvs(
        self,
        file_paths: list[Path],
        write_behaviour: WriteBehaviour,
        dry_run: DryRun = DryRun.WRITE,
    ) -> None:
        # Bundle timelist with data list
        data_lst: list = [
            (["time_list", "idx_list"], self.time_list, self.idx_list),
            (["time_list_ppg0", "ppg0_list"], self.time_list_ppg0, self.ppg0_list),
            (["time_list_ppg1", "ppg1_list"], self.time_list_ppg1, self.ppg1_list),
            (["time_list_ppg2", "ppg2_list"], self.time_list_ppg2, self.ppg2_list),
            (["time_list_ppg3", "ppg3_list"], self.time_list_ppg3, self.ppg3_list),
            (
                ["time_list_bioz_86", "bioz_list_86"],
                self.time_list_bioz_86,
                self.bioz_list_86,
            ),
            (
                ["time_list_ecg_86", "ecg_list_86"],
                self.time_list_ecg_86,
                self.ecg_list_86,
            ),
        ]

        # Check that we have received the correct number of file paths
        if len(file_paths) != len(data_lst):
            msg = f"Invalid number of file paths {len(file_paths)}"
            raise ValueError(msg)

        # End writing if dry run
        if dry_run == DryRun.NO_WRITES:
            return

        # Choose write mode between overwriting and appending
        mode = "w" if write_behaviour == WriteBehaviour.OVERWRITE else "a"

        # Go through each file and the corresponding data
        for file_path, (keys, time_list, data_list) in zip(
            file_paths,
            data_lst,
            strict=True,
        ):
            # Check if file was empty
            was_empty = not file_path.exists() or file_path.stat().st_size == 0

            # Open file
            with file_path.open(mode, encoding="utf-8") as file:
                # Create CSV writer
                writer = csv.DictWriter(file, fieldnames=keys)

                # Only write header if empty and appending, or when overwriting
                if (
                    was_empty and write_behaviour == WriteBehaviour.APPEND
                ) or write_behaviour == WriteBehaviour.OVERWRITE:
                    writer.writeheader()

                rows: list = []
                # Create rows
                for time, data in zip(time_list, data_list, strict=False):
                    rows.append({keys[0]: time, keys[1]: data})

                writer.writerows(rows)
```

##### _csv_filenames

This function is used to give a list of filenames for the CSV files. This list is then
used to create the list of file paths for the `_write_csvs` function.

It needs to be overridden if multiple CSV files are needed.

For example:

```python
@dataclass
class MAX86178(Sensor):
    @override
    @classmethod
    def _csv_filenames(cls) -> list[str]:
        # Create separate files for the indices, the PPGs, the ECG and BIOZ data
        suffixes = ["", "_ppg0", "_ppg1", "_ppg2", "_ppg3", "_bioz", "_ecg"]

        return [f"{cls.name()}{s}.csv" for s in suffixes]
```

##### write_data

This function is called when needing to write data into the database.

It can be overridden when needing to add additional files in the database (e.g. an audio
file for the microphone).

For example:

```python
@dataclass
class T5838(Sensor):
    @override
    def write_data(
        self,
        folder_path: Path,
        dry_run: DryRun = DryRun.WRITE,
        write_behaviour: WriteBehaviour = WriteBehaviour.APPEND,
    ) -> list[Path]:
        if self.is_empty():
            logger.debug("No data, skipped writing", sensor=self.name())
            return []

        # Write WAV file
        file_path = folder_path / f"{self.name()}.wav"

        if dry_run == DryRun.WRITE:
            self._write_audio_wav(file_path, write_behaviour=write_behaviour)

        # Write the CSVs
        return super().write_data(
            folder_path,
            dry_run=dry_run,
            write_behaviour=write_behaviour,
        )
```

### 3. Run the `generate_sensors_info.py` script

The `generate_sensors_info.py` automatically generates a Python file containing updated
data for the program for any new or removed sensors.

This can be run using this command:

```terminal
uv run -m scripts.generate_sensors_info
```

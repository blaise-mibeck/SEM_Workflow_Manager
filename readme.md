# SEM Image Workflow Manager

A desktop application for organizing, processing, and visualizing Scanning Electron Microscope (SEM) images.

## Features

- Session-based organization of SEM images
- Automatic metadata extraction from SEM images
- Multiple visualization workflows:
  - **MagGrid**: Creates hierarchical magnification visualizations
  - **CompareGrid**: Compares samples across different sessions
  - **ModeGrid**: Compares the same scene with different imaging modes (SED, BSD, Topo, ChemSEM)
- Export grids as PNG images with caption files for reports

## Installation

### Prerequisites

- Python 3.7 or higher

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/sem-workflow-manager.git
   cd sem-workflow-manager
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```
python main.py
```

### Workflow Steps

1. **Open Session Folder**: Select a folder containing SEM images.
2. **Enter Session Information**: Provide sample ID, type, preparation method, and operator name.
3. **Extract Metadata**: Use the Tools menu to extract metadata from images.
4. **Select Workflow**: Choose the appropriate workflow for your analysis.
5. **Configure Layout**: Adjust the grid layout as needed.
6. **Export Grid**: Save the visualization for use in reports.

## Session Information

The application organizes images into sessions, with each session having the following information:

### Session Fields

- **Sample ID**: Identifier used internally to identify the sample being imaged. This is the primary identifier used within the application.

- **TCL ID**: ID assigned by TCL to the original as-received sample. This may or may not be the same as the Sample ID, and is used for tracking samples through the lab system.

- **Client Sample Name**: Name or lot number assigned by the client. This is most meaningful to the client and may be how the sample is discussed in reports.

- **Sample Type**: A description of the physical form of the sample, such as:
  - Dry powder
  - Paste
  - Solid
  - Small part
  - Coating
  - Film
  - Granule
  - etc.

- **Preparation Method**: The method used to prepare the sample for SEM imaging, such as:
  - Flick
  - Dish
  - Dispersed
  - Drop cast
  - Cross-section
  - Adhered
  - Sputter coated
  - etc.

- **Operator Name**: The name of the person who operated the SEM for this session.

- **Notes**: Additional information about the session, sample, or imaging conditions.

These fields help organize and categorize the SEM images, making it easier to find and compare samples across sessions.

## ModeGrid Workflow

The ModeGrid workflow allows you to compare SEM images of the same scene captured with different imaging modes:

- **Secondary Electron (SED)**: Shows surface topography and provides information about surface details.
- **Backscatter Electron (BSD)**: Provides compositional contrast based on atomic number.
- **Topographic (Topo)**: Uses BSD detector segments to create shadow effects that enhance surface details from different directions.
- **ChemSEM**: Chemical imaging mode that provides elemental composition information.

### Using ModeGrid

1. Open a session containing SEM images in different modes
2. Switch to the "Mode Grid" tab
3. Click "Discover Collections" to find sets of images with the same scene but different modes
4. Select a collection and configure the grid layout
5. Click "Create Grid" to generate the visualization
6. Export the grid for reports or analysis

## Project Structure

```
sem_workflow_manager/
│
├── main.py                     # Application entry point
├── app.py                      # Main application class
├── utils/                      # Utility functions
│   ├── logger.py               # Logging utilities
│   └── config.py               # Configuration management
│
├── models/                     # Data models
│   ├── session.py              # Session data model
│   ├── metadata_extractor.py   # Metadata extraction module
│   └── image_metadata.py       # Image metadata model
│
├── workflows/                  # Workflow implementations
│   ├── workflow_base.py        # Base workflow class
│   ├── mag_grid.py             # MagGrid workflow
│   ├── compare_grid.py         # CompareGrid workflow
│   ├── mode_grid.py            # ModeGrid workflow
│   └── grid_generator.py       # Grid visualization generation
│
└── ui/                         # User interface components
    ├── main_window.py          # Main application window
    ├── session_panel.py        # Session information panel
    ├── workflow_panel.py       # Workflow selection panel
    ├── grid_preview.py         # Grid visualization preview
    └── mode_grid_panel.py      # ModeGrid control panel
```

## Metadata Fields

The application extracts and utilizes the following metadata from SEM images:

### Basic Information
- **filename**: Name of the image file
- **databar_label**: Text label from the databar in the image
- **acquisition_time**: Date and time when the image was acquired

### Image Dimensions
- **pixels_width**: Width of the image in pixels
- **pixels_height**: Height of the image in pixels
- **pixel_dimension_nm**: Size of each pixel in nanometers
- **field_of_view_width**: Width of the field of view in micrometers
- **field_of_view_height**: Height of the field of view in micrometers
- **magnification**: Calculated magnification of the image

### SEM Parameters
- **mode**: Detector type (SED, BSD, mix, etc.)
- **high_voltage_kV**: Acceleration voltage in kilovolts
- **working_distance_mm**: Working distance in millimeters
- **spot_size**: Beam spot size
- **dwell_time_ns**: Dwell time in nanoseconds
- **integrations**: Number of frame averages

### Sample Positioning
- **sample_position_x**: X-coordinate of sample position in micrometers
- **sample_position_y**: Y-coordinate of sample position in micrometers
- **multistage_x**: X-coordinate of multistage position
- **multistage_y**: Y-coordinate of multistage position
- **beam_shift_x**: X beam shift
- **beam_shift_y**: Y beam shift

### Image Adjustments
- **contrast**: Applied contrast adjustment
- **brightness**: Applied brightness adjustment
- **gamma**: Applied gamma correction

### Advanced Parameters
- **pressure_Pa**: Chamber pressure in pascals
- **emission_current_uA**: Emission current in microamperes
- **detector_segments**: For Topo mode - which BSD segments are active
- **detectorMixFactors**: Mix factors for different detector segments

## Configuration

Application settings are stored in `config.json`. This includes:

```json
{
  "recent_sessions": [],
  "max_recent_sessions": 10,
  "default_export_path": "~/Documents",
  "log_level": "INFO",
  "template_match_threshold": 0.5,
  "ui": {
    "theme": "default",
    "font_size": 10,
    "window_size": [1200, 800],
    "window_position": [100, 100]
  },
  "mode_grid": {
    "scene_match_tolerance": 0.3,
    "label_font_size": 12,
    "preferred_modes_order": ["sed", "bsd", "topo", "chemsem", "edx"],
    "label_mode": true,
    "label_voltage": true,
    "label_current": true,
    "label_integrations": true
  }
}
```

## License

[MIT License](LICENSE)

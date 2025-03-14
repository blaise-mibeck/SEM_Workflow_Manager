# SEM Image Workflow Manager

A desktop application for organizing, processing, and visualizing Scanning Electron Microscope (SEM) images.

## Features

- Session-based organization of SEM images
- Automatic metadata extraction from SEM images
- MagGrid workflow for creating hierarchical magnification visualizations
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
4. **Select Workflow**: Choose the MagGrid workflow for hierarchical visualizations.
5. **Select Collection**: Choose a discovered collection or refresh to find more.
6. **Configure Layout**: Adjust the grid layout as needed.
7. **Export Grid**: Save the visualization for use in reports.

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
│   └── grid_generator.py       # Grid visualization generation
│
└── ui/                         # User interface components
    ├── main_window.py          # Main application window
    ├── session_panel.py        # Session information panel
    ├── workflow_panel.py       # Workflow selection panel
    └── grid_preview.py         # Grid visualization preview
```

## Logging

Logs are stored in the `logs` directory. Each module logs its own activities, making it easy to track what's happening in the application.

## Configuration

Application settings are stored in `config.json`. This includes recent sessions, default paths, and UI preferences.

## License

[MIT License](LICENSE)

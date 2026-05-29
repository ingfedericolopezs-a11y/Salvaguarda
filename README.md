# ROESAN-SALVAGUARDAR 🛡️

**Monthly Insurance Policy Reconciliation Application**

A modern web application for processing and reconciling monthly movements (entries and withdrawals) for the Salvaguardar insurance policy. Built with Flask and Python.

## Features ✨

- 📊 **Master Template Processing** - Upload and process master billing templates
- 🔄 **Movement Files Integration** - Merge and reconcile entry/withdrawal movements
- 🔍 **Cedula Search** - Search for specific insured individuals across all files
- 📁 **File Management** - Organize and download processed files with detailed history
- 📈 **Progress Indicators** - Visual progress bars during file processing
- 🎨 **Modern UI** - Beautiful, responsive glass-morphism design with ROESAN brand colors
- ⚡ **Dynamic Data Filtering** - Real-time table filtering in preview section
- 🎯 **Enhanced Validation** - Comprehensive file and input validation with helpful error messages
- 📱 **Fully Responsive** - Optimized for desktop, tablet, and mobile devices
- ✅ **File Selection Feedback** - Visual feedback for file selection with size summaries

## System Requirements

- Python 3.9+
- pip or poetry (for dependency management)
- 100MB+ free disk space
- 2GB+ RAM recommended

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ROESAN-SALVAGUARDAR.git
cd ROESAN-SALVAGUARDAR/ROESAN-SALVAGUARDAR
```

### 2. Create Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings (optional - defaults work fine)
# nano .env
```

### 5. Run the Application
```bash
python app.py
```

The application will be available at: **http://localhost:5000**

## Configuration

Configuration options are defined in `config.py` and can be overridden using environment variables via the `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | production | Environment mode (development/production) |
| `FLASK_DEBUG` | False | Enable/disable debug mode |
| `FLASK_HOST` | 0.0.0.0 | Server host address |
| `FLASK_PORT` | 5000 | Server port number |
| `UPLOAD_DIR` | uploads | Temporary upload directory |
| `OUTPUT_DIR` | outputs | Processed files output directory |
| `WORKSPACE_DIR` | . | Workspace root directory for file scanning |
| `MAX_FILE_SIZE` | 10485760 | Maximum file size (10 MB) in bytes |
| `LOG_LEVEL` | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |

## Usage

### 1. Processing Tab (Main Workflow)

1. **Upload Master File**
   - Click on "Plantilla Maestro / Cobro Anterior"
   - Select the previous month's billing template (`PLANTILLA CARGUE COBRO`)
   
2. **Upload Movement Files**
   - Click on "Archivos de Movimientos"
   - Select one or more files containing INGRESOS (entries) and RETIROS (withdrawals)

3. **Start Reconciliation**
   - Click "Iniciar Conciliación"
   - Monitor progress in the execution console
   - View statistics and generated files upon completion

4. **Download Results**
   - Click download buttons to save:
     - `INGRESOS_Y_RETIROS_GENERADOS_[MONTH]_[YEAR].xlsx`
     - `PLANTILLA_CARGUE_COBRO_[MONTH]_[YEAR].xlsx`

### 2. Search Tab

1. Enter a cédula (document number) in the search field
2. Click "Buscar"
3. View all matching records across all files
4. Results show file location, sheet, and complete row data

### 3. History Tab

View all Excel files in your workspace with:
- File name
- Type (output, workspace, or upload)
- File size
- Last modification date
- Download option

## File Format Requirements

### Master File (PLANTILLA CARGUE COBRO)
Must contain columns:
- NUMERO_IDENTIFICACION_ASEGURADO
- CARGO
- GENERO
- FECHA_NACIMIENTO_ASEGURADO
- VALOR_ASEGURADO_MUERTE

### Movement Files (INGRESOS / RETIROS)
Must contain sheets named `INGRESOS` or `RETIROS` with columns:
- Identification column (various names accepted: IDENTIFICACION, C.C., CEDULA, etc.)
- Name column (NOMBRE, RAZON SOCIAL, APELLIDO, etc.)
- Optional: FECHA_NACIMIENTO, date columns

The application auto-detects headers and flexibly maps column names.

## Project Structure

```
ROESAN-SALVAGUARDAR/
├── app.py                  # Main Flask application
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment variables
├── README.md              # This file
├── utils/
│   ├── __init__.py
│   ├── validators.py      # Input validation and cleaning
│   ├── data_processor.py  # Core Excel processing logic
│   └── file_handler.py    # File system operations
├── static/
│   ├── css/styles.css     # Application styles
│   └── js/app.js          # Frontend JavaScript
├── templates/
│   └── index.html         # Main HTML template
├── uploads/               # Temporary upload storage
└── outputs/               # Processed files output
```

## API Endpoints

### GET `/`
Serves the main application page.

### GET `/api/history`
Returns list of all Excel files with metadata.
```json
[
  {
    "name": "file.xlsx",
    "type": "output",
    "size": 102400,
    "modified": "2026-05-29 14:30:00",
    "path": "/full/path/to/file.xlsx"
  }
]
```

### POST `/api/process`
Process master and movement files.

**Form Data:**
- `master_file`: Master template file
- `movement_files`: One or more movement files

**Response:**
```json
{
  "status": "success",
  "statistics": {
    "total_movements": 150,
    "total_ingresos": 75,
    "total_retiros": 75,
    "master_total_before": 500,
    "master_total_after": 425
  },
  "filenames": {
    "movements": "INGRESOS_Y_RETIROS_GENERADOS_MAY_2026.xlsx",
    "master": "PLANTILLA_CARGUE_COBRO_MAY_2026.xlsx"
  },
  "preview_movements": [...],
  "preview_master": [...],
  "logs": [...]
}
```

### GET `/api/download/<filename>`
Download a processed file.

**Parameters:**
- `filename`: Name of file to download

### GET `/api/search`
Search for cedula across all files.

**Query Parameters:**
- `cedula`: Document number to search for

**Response:**
```json
[
  {
    "file": "filename.xlsx",
    "folder": "outputs",
    "sheet": "GENERAL",
    "row": 42,
    "data": {...}
  }
]
```

## Security Considerations

✅ **Implemented:**
- File type validation (MIME type and extension)
- File size limits (configurable, default 10MB)
- Directory traversal prevention
- Secure file handling with `werkzeug.utils.secure_filename`
- Input sanitization and validation
- Comprehensive error handling
- Logging of operations and errors

## Development

### Enable Debug Mode
```bash
# Set in .env
FLASK_DEBUG=True
FLASK_ENV=development
```

### Run Tests (Future)
```bash
pytest tests/
```

### Code Style
The project follows PEP 8 conventions. Format code with:
```bash
black app.py utils/
```

## Troubleshooting

### Issue: "File too large" error
**Solution:** Increase `MAX_FILE_SIZE` in `.env`

### Issue: Headers not detected
**Solution:** Ensure movement files have headers in first 20 rows with common keywords (IDENTIFICACION, NOMBRE, etc.)

### Issue: Column mapping errors
**Solution:** Check that master file has the required columns listed in "File Format Requirements"

### Issue: Files not appearing in History
**Solution:** Ensure files are in the configured `UPLOAD_DIR`, `OUTPUT_DIR`, or `WORKSPACE_DIR`

## Logging

Application logs are written to:
- **Console**: Real-time display
- **File**: `app.log` in the application directory

Adjust log level in `.env`:
```
LOG_LEVEL=DEBUG    # Verbose logging
LOG_LEVEL=INFO     # Normal logging
LOG_LEVEL=ERROR    # Only errors
```

## Performance Tips

1. **Split large files** - Process files <5MB for faster results
2. **Use SSD storage** - Faster file I/O operations
3. **Close other applications** - Free up system resources
4. **Monitor logs** - Check `app.log` for bottlenecks

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions:
- 📧 Email: [your-email@example.com]
- 🐛 GitHub Issues: [Create an issue]
- 📖 Documentation: [Wiki/Docs]

## Changelog

### Version 1.1 (2026-05-29) - Enhanced UI/UX
- **Visual Improvements**
  - Added ROESAN brand logo and color scheme
  - Enhanced upload zones with better visual feedback
  - Improved table styling with gradient headers
  - Better hover effects and animations throughout
  - Visual progress bar during processing
  
- **Functional Improvements**
  - Real-time table data filtering
  - Better file validation with detailed error messages
  - File selection counter with size summary
  - Enhanced search functionality with keyboard support
  - Improved error handling and user feedback
  
- **UI Enhancements**
  - Better tooltips and helpful hints
  - Smooth transitions and animations
  - Improved responsive design
  - Better color consistency with brand identity

### Version 1.0 (2026-05-29)
- Initial release
- Multi-file processing support
- Real-time execution logs
- Cedula search functionality
- File history management
- Modern responsive UI

## Authors

- **Developer**: Your Name
- **Organization**: ROESAN Seguros

## Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Data processing with [Pandas](https://pandas.pydata.org/)
- Frontend styling inspired by modern glass-morphism design

---

Made with ❤️ by ROESAN Team | © 2026 ROESAN Seguros. All rights reserved.

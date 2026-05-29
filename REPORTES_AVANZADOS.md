# Sistema de Reportes Avanzados 📊

## Descripción General

El sistema de reportes avanzados proporciona análisis exhaustivos y generación de reportes profesionales para la conciliación mensual de la póliza Salvaguardar. Los reportes incluyen visualizaciones, estadísticas detalladas e insights automáticos de negocio.

## Características Principales

### 1. Generación de Reportes PDF 📄
- **Múltiples páginas profesionales**
  - Página 1: Resumen ejecutivo con 4 KPIs principales
  - Página 2: Análisis de distribuciones con gráficos
  - Página 3: Estadísticas detalladas e insights

- **Visualizaciones incluidas**
  - Gráficos circulares (pie charts) para distribución de movimientos
  - Gráficos de barras para distribución por género
  - Gráficos de barras horizontales para top 8 cargos
  - Tablas de estadísticas resumidas

- **Formato profesional**
  - Marca ROESAN-SALVAGUARDAR en encabezado
  - Colores corporativos (#667eea, #10b981, #ef4444)
  - Tipografía clara y legible
  - Fallback automático si matplotlib no está disponible

### 2. Exportación a Excel 📊
- **Múltiples hojas analíticas**
  - **Resumen**: KPIs principales (total movimientos, ingresos, retiros, neto)
  - **Movimientos**: Datos completos de movimientos procesados
  - **Plantilla**: Plantilla de cobro actualizada
  - **Estadísticas**: Desglose por tipo, género y cargo
  - **Insights**: Mensajes de insights de negocio generados

- **Características**
  - Datos completos sin limitación de filas
  - Formato estructurado y fácil de analizar
  - Compatible con Excel, LibreOffice, Google Sheets
  - Preserva tipos de datos

### 3. Motor de Análisis 🎯
El módulo `ReportGenerator` incluye análisis automáticos:

- **Resumen de Movimientos**
  - Total de movimientos procesados
  - Desglose ingresos vs retiros
  - Movimiento neto (diferencia)
  - Porcentaje de registros afectados

- **Estadísticas Detalladas**
  - Conteo por tipo (INGRESO/RETIRO)
  - Distribución por género
  - Distribución por cargo (posición)
  - Valores agregados por categoría

- **Análisis de Distribuciones**
  - Distribución de géneros (F/M/Otro)
  - Distribución de cargos principales
  - Distribución de tipos de movimiento
  - Porcentajes calculados

- **Tendencias Temporales**
  - Total de registros procesados
  - Promedio diario
  - Eficiencia de procesamiento
  - Métricas de desempeño

### 4. Generación de Insights 💡
El sistema genera automáticamente insights de negocio:

**Ejemplos de insights generados:**
- ✓ Positive balance: 45 más ingresos que retiros
- ⚠ More withdrawals: 20 más retiros que ingresos
- ✓ Gender distribution: Femenino (65%)
- Data quality score: 98.5% (completitud de datos)

## Integración en la Aplicación

### API Endpoints

#### 1. Generar Reporte PDF
```http
POST /api/reports/pdf
Content-Type: application/json

Response:
{
  "status": "success",
  "filename": "REPORTE_CONCILIACION_20260529_152903.pdf",
  "filepath": "/path/to/file",
  "message": "Reporte PDF generado exitosamente"
}
```

#### 2. Generar Reporte Excel
```http
POST /api/reports/excel
Content-Type: application/json

Response:
{
  "status": "success",
  "filename": "REPORTE_CONCILIACION_20260529_152903.xlsx",
  "filepath": "/path/to/file",
  "message": "Reporte Excel generado exitosamente"
}
```

#### 3. Descargar Reporte
```http
GET /api/reports/download/{filename}

Response: Binary file with appropriate MIME type
```

### Interfaz de Usuario

**Ubicación:** Tab "Procesar Mes" → Sección "Reportes Avanzados" (visible después del procesamiento exitoso)

**Botones disponibles:**
- 📄 **Generar PDF** - Crea reporte PDF profesional con gráficos
- 📊 **Generar Excel** - Crea libro Excel con análisis detallado

**Flujo de usuario:**
1. Usuario carga archivos y procesa datos
2. Después del procesamiento exitoso, ve la sección "Reportes Avanzados"
3. Hace clic en "Generar PDF" o "Generar Excel"
4. El servidor procesa y genera el reporte
5. El archivo se descarga automáticamente
6. Se muestra confirmación visual en la interfaz

## Estructura del Código

### Módulo: `utils/report_generator.py`

```python
class ReportGenerator:
    """Motor de generación de reportes avanzados"""
    
    def generate_movement_analytics() -> Dict
        """Genera análisis completos de movimientos"""
    
    def generate_pdf_report() -> str
        """Genera reporte PDF profesional"""
    
    def export_to_excel() -> str
        """Exporta análisis a Excel"""
    
    def _generate_summary() -> Dict
        """Calcula estadísticas resumidas"""
    
    def _calculate_statistics() -> Dict
        """Calcula estadísticas detalladas"""
    
    def _analyze_distributions() -> Dict
        """Analiza distribuciones de datos"""
    
    def _analyze_trends() -> Dict
        """Analiza tendencias temporales"""
    
    def _generate_insights() -> List[str]
        """Genera insights de negocio"""
```

### Integración en `app.py`

```python
# Inicialización
report_generator = ReportGenerator(config.OUTPUT_DIR)

# Almacenamiento de datos procesados
last_processed_data = {
    'movements_df': None,
    'master_df': None,
    'analytics': None
}

# Endpoints de reportes
@app.route('/api/reports/pdf', methods=['POST'])
@app.route('/api/reports/excel', methods=['POST'])
@app.route('/api/reports/download/<path:filename>', methods=['GET'])
```

### Frontend: `static/js/app.js`

```javascript
// Funciones principales
async function generatePdfReport()
async function generateExcelReport()

// Manejo de UI
- Deshabilitación de botones durante procesamiento
- Mostrar/ocultar spinner de carga
- Actualizar texto del botón
- Manejar errores con notificaciones
- Iniciar descargas automáticas
```

### Estilos: `static/css/styles.css`

```css
/* Nuevo botón gradient para reportes */
.btn-gradient {
    background: linear-gradient(135deg, #7c3aed 0%, #667eea 50%, #06b6d4 100%);
    color: white;
    box-shadow: 0 0 20px rgba(124, 58, 237, 0.3);
}

/* Sección de reportes */
.reports-section {
    padding: var(--spacing-lg);
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.1) 0%, ...);
    border: 1px solid rgba(124, 58, 237, 0.2);
    margin-top: var(--spacing-lg);
}
```

## Ejemplos de Reportes

### Datos de Ejemplo

Supongamos que se procesa un archivo con:
- 150 movimientos totales
- 90 ingresos
- 60 retiros
- 65% género femenino
- 35% género masculino
- 8 cargos principales

### Contenido del Reporte PDF

**Página 1 - Resumen:**
```
┌─────────────────────────────────┐
│  ROESAN-SALVAGUARDAR           │
│  Reporte de Conciliación        │
├─────────────────────────────────┤
│ 150        │ 90         │ 60      │ +30      │
│ Movimientos│ Ingresos   │ Retiros │ Neto    │
└─────────────────────────────────┘
```

**Página 2 - Gráficos:**
- Pie chart: 60% Ingresos, 40% Retiros
- Bar chart: Géneros (Femenino 65%, Masculino 35%)
- Horizontal bar: Top 8 cargos

**Página 3 - Insights:**
- ✓ Positive balance: 30 más ingresos que retiros
- Distribución de géneros: Femenino (65%)
- Data quality score: 99.2%
- Tendencias: Promedio diario 5 movimientos

### Contenido del Reporte Excel

| Sheet | Contenido |
|-------|-----------|
| Resumen | KPIs principales |
| Movimientos | Todos los registros de movimientos |
| Plantilla | Plantilla de cobro actualizada |
| Estadísticas | Desglose por tipo/género/cargo |
| Insights | Mensajes de insights |

## Características Técnicas

### Manejo de Errores
- ✓ Validación de datos disponibles antes de generar
- ✓ Fallback automático si matplotlib no está disponible
- ✓ Fallback a reportlab si matplotlib falla
- ✓ Fallback a texto si ambos fallan
- ✓ Mensajes de error descriptivos al usuario

### Rendimiento
- ✓ Generación rápida incluso con miles de registros
- ✓ Uso eficiente de memoria con streaming
- ✓ Caché de análisis para múltiples descargas
- ✓ Procesamiento en background

### Seguridad
- ✓ Validación de rutas (prevención de directory traversal)
- ✓ MIME types correctos para descargas
- ✓ Manejo seguro de archivos
- ✓ Validación de datos antes de procesamiento

### Compatibilidad
- ✓ PDF compatible con todos los lectores PDF
- ✓ Excel compatible con Excel 2007+, LibreOffice, Google Sheets
- ✓ Caracteres especiales y acentos preservados
- ✓ Formatos de datos correctos

## Instrucciones de Uso

### Para Usuarios

1. **Procesar Archivos**
   - Carga la plantilla maestro
   - Carga los archivos de movimientos
   - Haz clic en "Iniciar Conciliación"

2. **Generar Reportes**
   - Después del procesamiento, verás la sección "Reportes Avanzados"
   - Haz clic en "Generar PDF" o "Generar Excel"
   - El reporte se descargará automáticamente

3. **Analizar Resultados**
   - Abre el reporte descargado
   - Revisa los KPIs y gráficos
   - Consulta los insights automáticos
   - Usa los datos para tomar decisiones

### Para Desarrolladores

1. **Extender análisis**
   ```python
   # En ReportGenerator
   def _analyze_custom_metric(self, df) -> Dict:
       # Tu código de análisis
       return custom_analytics
   ```

2. **Agregar nuevas hojas Excel**
   ```python
   # En export_to_excel
   custom_df.to_excel(writer, sheet_name='Mi Hoja', index=False)
   ```

3. **Personalizar gráficos**
   ```python
   # En _create_charts_page
   # Modifica colores, tipos de gráficos, etiquetas
   ```

## Requisitos

- Python 3.9+
- pandas (para análisis de datos)
- openpyxl (para exportación a Excel)
- matplotlib (para gráficos PDF - opcional, con fallback)
- reportlab (fallback para PDF)

## Futuras Mejoras

- [ ] Agregar gráficos de tendencias temporales
- [ ] Implementar filtros personalizables en reportes
- [ ] Agregar comparativa con períodos anteriores
- [ ] Implementar envío de reportes por email
- [ ] Agregar marca de agua personalizada
- [ ] Implementar reportes programados
- [ ] Agregar más tipos de gráficos (scatter, line, etc)
- [ ] Implementar exportación a otros formatos (PowerPoint, Word)

## Soporte

Para issues, preguntas o sugerencias sobre los reportes:
- Revisa la sección de troubleshooting
- Verifica los logs en `app.log`
- Contacta al equipo de desarrollo

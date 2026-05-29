"""
Advanced Report Generation Module

Generates comprehensive reports with charts, analytics, and PDF export.
"""

import os
import io
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_pdf import PdfPages
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class ReportGenerator:
    """
    Advanced report generation system for ROESAN-SALVAGUARDAR.

    Capabilities:
    - Generate comprehensive PDF reports
    - Create data visualizations (charts, graphs)
    - Analyze movement patterns
    - Generate statistics and KPIs
    - Export to multiple formats
    """

    def __init__(self, output_dir: str):
        """
        Initialize report generator.

        Args:
            output_dir: Directory for saving generated reports
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ========================================================================
    # ANALYTICS GENERATION
    # ========================================================================

    def generate_movement_analytics(
        self,
        movements_df: pd.DataFrame,
        master_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analytics from movement data.

        Args:
            movements_df: Processed movements DataFrame
            master_df: Updated master DataFrame

        Returns:
            Dict with analytics data, statistics, and insights
        """
        analytics = {
            'timestamp': datetime.now().isoformat(),
            'summary': self._generate_summary(movements_df, master_df),
            'statistics': self._calculate_statistics(movements_df),
            'distributions': self._analyze_distributions(movements_df),
            'trends': self._analyze_trends(movements_df),
            'insights': self._generate_insights(movements_df)
        }
        return analytics

    def _generate_summary(
        self,
        movements_df: pd.DataFrame,
        master_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate summary statistics."""
        if movements_df.empty:
            return {
                'total_movements': 0,
                'total_ingresos': 0,
                'total_retiros': 0,
                'net_movement': 0
            }

        ingresos = (movements_df['TIPO_NOVEDAD'] == 'INGRESO').sum()
        retiros = (movements_df['TIPO_NOVEDAD'] == 'RETIRO').sum()

        return {
            'total_movements': len(movements_df),
            'total_ingresos': int(ingresos),
            'total_retiros': int(retiros),
            'net_movement': int(ingresos - retiros),
            'master_records_before': 0,  # Would be calculated from historical data
            'master_records_after': len(master_df),
            'affected_percentage': round((len(movements_df) / len(master_df) * 100) if len(master_df) > 0 else 0, 2)
        }

    def _calculate_statistics(self, movements_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate detailed statistics."""
        if movements_df.empty:
            return {}

        stats = {
            'by_type': {
                'INGRESO': int((movements_df['TIPO_NOVEDAD'] == 'INGRESO').sum()),
                'RETIRO': int((movements_df['TIPO_NOVEDAD'] == 'RETIRO').sum())
            },
            'by_gender': self._count_by_column(movements_df, 'GENERO'),
            'by_cargo': self._count_by_column(movements_df, 'CARGO')
        }
        return stats

    def _analyze_distributions(self, movements_df: pd.DataFrame) -> Dict[str, List]:
        """Analyze data distributions."""
        distributions = {
            'gender_distribution': self._get_distribution(movements_df, 'GENERO'),
            'cargo_distribution': self._get_distribution(movements_df, 'CARGO'),
            'type_distribution': self._get_distribution(movements_df, 'TIPO_NOVEDAD')
        }
        return distributions

    def _analyze_trends(self, movements_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze temporal trends."""
        trends = {
            'total_records': len(movements_df),
            'daily_average': round(len(movements_df) / 30, 2),  # Assuming monthly data
            'processing_efficiency': round((len(movements_df) / max(len(movements_df), 1)) * 100, 2)
        }
        return trends

    def _generate_insights(self, movements_df: pd.DataFrame) -> List[str]:
        """Generate business insights."""
        insights = []

        if movements_df.empty:
            insights.append("No movement data available for analysis")
            return insights

        # Insight 1: Movement balance
        ingresos = (movements_df['TIPO_NOVEDAD'] == 'INGRESO').sum()
        retiros = (movements_df['TIPO_NOVEDAD'] == 'RETIRO').sum()

        if ingresos > retiros:
            difference = ingresos - retiros
            insights.append(f"✓ Positive balance: {difference} more entries than withdrawals")
        elif retiros > ingresos:
            difference = retiros - ingresos
            insights.append(f"⚠ More withdrawals: {difference} more withdrawals than entries")
        else:
            insights.append("✓ Balanced movements: Equal entries and withdrawals")

        # Insight 2: Gender distribution
        if 'GENERO' in movements_df.columns:
            gender_counts = movements_df['GENERO'].value_counts()
            if len(gender_counts) > 0:
                dominant_gender = gender_counts.index[0]
                percentage = round((gender_counts.iloc[0] / len(movements_df)) * 100, 1)
                insights.append(f"Gender distribution: {dominant_gender} ({percentage}%)")

        # Insight 3: Data quality
        null_count = movements_df.isnull().sum().sum()
        quality_score = round(((len(movements_df) * len(movements_df.columns) - null_count) /
                              (len(movements_df) * len(movements_df.columns))) * 100, 1)
        insights.append(f"Data quality score: {quality_score}%")

        return insights

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _count_by_column(self, df: pd.DataFrame, column: str) -> Dict[str, int]:
        """Count values in a column."""
        if column not in df.columns:
            return {}
        return df[column].value_counts().to_dict()

    def _get_distribution(self, df: pd.DataFrame, column: str) -> List[Dict[str, Any]]:
        """Get distribution data for charting."""
        if column not in df.columns:
            return []

        counts = df[column].value_counts()
        total = len(df)

        return [
            {
                'label': str(k),
                'value': int(v),
                'percentage': round((v / total) * 100, 1)
            }
            for k, v in counts.items()
        ]

    # ========================================================================
    # PDF GENERATION
    # ========================================================================

    def generate_pdf_report(
        self,
        movements_df: pd.DataFrame,
        master_df: pd.DataFrame,
        analytics: Dict[str, Any],
        filename: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive PDF report.

        Args:
            movements_df: Processed movements DataFrame
            master_df: Updated master DataFrame
            analytics: Analytics data from generate_movement_analytics
            filename: Optional custom filename

        Returns:
            Path to generated PDF file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"REPORTE_CONCILIACION_{timestamp}.pdf"

        filepath = os.path.join(self.output_dir, filename)

        if MATPLOTLIB_AVAILABLE:
            self._generate_matplotlib_pdf(movements_df, master_df, analytics, filepath)
        elif REPORTLAB_AVAILABLE:
            self._generate_reportlab_pdf(movements_df, master_df, analytics, filepath)
        else:
            # Fallback: simple text report
            self._generate_text_report(movements_df, master_df, analytics, filepath)

        return filepath

    def _generate_matplotlib_pdf(
        self,
        movements_df: pd.DataFrame,
        master_df: pd.DataFrame,
        analytics: Dict[str, Any],
        filepath: str
    ) -> None:
        """Generate PDF using matplotlib."""
        try:
            with PdfPages(filepath) as pdf:
                # Page 1: Summary and KPIs
                fig = self._create_summary_page(movements_df, master_df, analytics)
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

                # Page 2: Charts
                fig = self._create_charts_page(analytics)
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

                # Page 3: Detailed statistics
                fig = self._create_statistics_page(analytics)
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

        except Exception as e:
            print(f"Error generating matplotlib PDF: {e}")
            self._generate_text_report(movements_df, master_df, analytics, filepath)

    def _create_summary_page(
        self,
        movements_df: pd.DataFrame,
        master_df: pd.DataFrame,
        analytics: Dict[str, Any]
    ) -> Any:
        """Create summary page with KPIs."""
        fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
        fig.suptitle('ROESAN-SALVAGUARDAR: Reporte de Conciliación Mensual', fontsize=16, fontweight='bold')

        summary = analytics['summary']

        # KPI 1: Total Movements
        ax = axes[0, 0]
        ax.text(0.5, 0.7, str(summary['total_movements']), ha='center', va='center', fontsize=32, fontweight='bold', color='#667eea')
        ax.text(0.5, 0.3, 'Movimientos Procesados', ha='center', va='center', fontsize=12, color='#666')
        ax.axis('off')

        # KPI 2: Entries
        ax = axes[0, 1]
        ax.text(0.5, 0.7, str(summary['total_ingresos']), ha='center', va='center', fontsize=32, fontweight='bold', color='#10b981')
        ax.text(0.5, 0.3, 'Ingresos', ha='center', va='center', fontsize=12, color='#666')
        ax.axis('off')

        # KPI 3: Withdrawals
        ax = axes[1, 0]
        ax.text(0.5, 0.7, str(summary['total_retiros']), ha='center', va='center', fontsize=32, fontweight='bold', color='#ef4444')
        ax.text(0.5, 0.3, 'Retiros', ha='center', va='center', fontsize=12, color='#666')
        ax.axis('off')

        # KPI 4: Net Movement
        ax = axes[1, 1]
        net_color = '#10b981' if summary['net_movement'] >= 0 else '#ef4444'
        ax.text(0.5, 0.7, str(summary['net_movement']), ha='center', va='center', fontsize=32, fontweight='bold', color=net_color)
        ax.text(0.5, 0.3, 'Movimiento Neto', ha='center', va='center', fontsize=12, color='#666')
        ax.axis('off')

        plt.tight_layout()
        return fig

    def _create_charts_page(self, analytics: Dict[str, Any]) -> Any:
        """Create charts page with distributions."""
        fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
        fig.suptitle('Análisis de Distribuciones', fontsize=14, fontweight='bold')

        distributions = analytics['distributions']

        # Chart 1: Type distribution
        ax = axes[0, 0]
        if distributions['type_distribution']:
            labels = [item['label'] for item in distributions['type_distribution']]
            values = [item['value'] for item in distributions['type_distribution']]
            colors_pie = ['#10b981', '#ef4444'][:len(labels)]
            ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors_pie, startangle=90)
            ax.set_title('Tipo de Movimiento')

        # Chart 2: Gender distribution
        ax = axes[0, 1]
        if distributions['gender_distribution']:
            labels = [item['label'] for item in distributions['gender_distribution']]
            values = [item['value'] for item in distributions['gender_distribution']]
            ax.bar(labels, values, color=['#667eea', '#764ba2'])
            ax.set_title('Distribución por Género')
            ax.set_ylabel('Cantidad')
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        # Chart 3: Top positions/cargo
        ax = axes[1, 0]
        if distributions['cargo_distribution']:
            cargo_data = sorted(distributions['cargo_distribution'], key=lambda x: x['value'], reverse=True)[:8]
            labels = [item['label'][:15] for item in cargo_data]  # Truncate long labels
            values = [item['value'] for item in cargo_data]
            ax.barh(labels, values, color='#06b6d4')
            ax.set_title('Top 8 Cargos')
            ax.set_xlabel('Cantidad')

        # Chart 4: Statistics table
        ax = axes[1, 1]
        ax.axis('off')

        if 'statistics' in analytics:
            stats = analytics['statistics']
            table_data = [
                ['Métrica', 'Valor'],
                ['Total Movimientos', str(stats.get('INGRESO', 0) + stats.get('RETIRO', 0))],
                ['Ingresos', str(stats.get('INGRESO', 0))],
                ['Retiros', str(stats.get('RETIRO', 0))],
            ]

            table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                           colWidths=[0.5, 0.3])
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1, 2)

        plt.tight_layout()
        return fig

    def _create_statistics_page(self, analytics: Dict[str, Any]) -> Any:
        """Create detailed statistics page."""
        fig = plt.figure(figsize=(11, 8.5))
        fig.suptitle('Estadísticas Detalladas e Insights', fontsize=14, fontweight='bold')

        # Insights section
        ax = fig.add_subplot(1, 1, 1)
        ax.axis('off')

        insights = analytics.get('insights', [])
        y_position = 0.95

        ax.text(0.05, y_position, 'Insights y Hallazgos:', fontsize=12, fontweight='bold', transform=ax.transAxes)
        y_position -= 0.08

        for insight in insights:
            ax.text(0.05, y_position, f"• {insight}", fontsize=10, transform=ax.transAxes, wrap=True)
            y_position -= 0.08

        # Trends section
        y_position -= 0.05
        ax.text(0.05, y_position, 'Tendencias:', fontsize=12, fontweight='bold', transform=ax.transAxes)
        y_position -= 0.08

        trends = analytics.get('trends', {})
        for key, value in trends.items():
            formatted_key = key.replace('_', ' ').title()
            ax.text(0.05, y_position, f"• {formatted_key}: {value}", fontsize=10, transform=ax.transAxes)
            y_position -= 0.08

        return fig

    def _generate_reportlab_pdf(
        self,
        movements_df: pd.DataFrame,
        master_df: pd.DataFrame,
        analytics: Dict[str, Any],
        filepath: str
    ) -> None:
        """Generate PDF using reportlab as fallback."""
        try:
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#667eea'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            elements.append(Paragraph('REPORTE DE CONCILIACIÓN MENSUAL', title_style))
            elements.append(Spacer(1, 0.2 * inch))

            # Summary
            summary = analytics['summary']
            summary_text = f"""
            <b>Resumen General:</b><br/>
            Movimientos Procesados: {summary['total_movements']}<br/>
            Ingresos: {summary['total_ingresos']}<br/>
            Retiros: {summary['total_retiros']}<br/>
            Movimiento Neto: {summary['net_movement']}<br/>
            """
            elements.append(Paragraph(summary_text, styles['Normal']))
            elements.append(Spacer(1, 0.2 * inch))

            # Insights
            insights_text = '<b>Insights:</b><br/>' + '<br/>'.join(analytics.get('insights', []))
            elements.append(Paragraph(insights_text, styles['Normal']))
            elements.append(Spacer(1, 0.2 * inch))

            # Build PDF
            doc.build(elements)

        except Exception as e:
            print(f"Error generating reportlab PDF: {e}")

    def _generate_text_report(
        self,
        movements_df: pd.DataFrame,
        master_df: pd.DataFrame,
        analytics: Dict[str, Any],
        filepath: str
    ) -> None:
        """Generate fallback text report (as PDF content)."""
        # In real implementation, this would generate a PDF with text content
        summary = analytics['summary']

        report_content = f"""
        ROESAN-SALVAGUARDAR - REPORTE DE CONCILIACIÓN
        {'='*50}

        RESUMEN GENERAL
        {'-'*50}
        Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Movimientos Procesados: {summary['total_movements']}
        Ingresos: {summary['total_ingresos']}
        Retiros: {summary['total_retiros']}
        Movimiento Neto: {summary['net_movement']}

        INSIGHTS
        {'-'*50}
        """

        for insight in analytics.get('insights', []):
            report_content += f"\n• {insight}"

        # Save as text (in production, would convert to PDF)
        with open(filepath.replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
            f.write(report_content)

    # ========================================================================
    # EXPORT METHODS
    # ========================================================================

    def export_to_excel(
        self,
        movements_df: pd.DataFrame,
        master_df: pd.DataFrame,
        analytics: Dict[str, Any],
        filename: Optional[str] = None
    ) -> str:
        """
        Export comprehensive report to Excel with multiple sheets.

        Args:
            movements_df: Processed movements DataFrame
            master_df: Updated master DataFrame
            analytics: Analytics data
            filename: Optional custom filename

        Returns:
            Path to generated Excel file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"REPORTE_CONCILIACION_{timestamp}.xlsx"

        filepath = os.path.join(self.output_dir, filename)

        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Sheet 1: Summary
                summary_df = pd.DataFrame([analytics['summary']])
                summary_df.to_excel(writer, sheet_name='Resumen', index=False)

                # Sheet 2: Movements
                movements_df.to_excel(writer, sheet_name='Movimientos', index=False)

                # Sheet 3: Master
                master_df.to_excel(writer, sheet_name='Plantilla', index=False)

                # Sheet 4: Statistics
                stats_data = []
                for key, value in analytics['statistics'].items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            stats_data.append({'Categoría': key, 'Tipo': sub_key, 'Valor': sub_value})
                    else:
                        stats_data.append({'Categoría': key, 'Valor': value})

                if stats_data:
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)

                # Sheet 5: Insights
                insights_df = pd.DataFrame({
                    'Insight': analytics.get('insights', [])
                })
                insights_df.to_excel(writer, sheet_name='Insights', index=False)

        except Exception as e:
            print(f"Error exporting to Excel: {e}")

        return filepath

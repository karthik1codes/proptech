"""
PDF Report Generator
Generates PDF reports for property analytics with user-specific state
"""

import io
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)

# Location risk data
LOCATION_RISK_DATA = {
    "bangalore": {
        "city": "Bangalore",
        "risks": ["Water Scarcity", "Traffic Congestion", "IT Sector Dependency"],
        "grid_factor": 0.82
    },
    "mumbai": {
        "city": "Mumbai", 
        "risks": ["Flooding", "Coastal Erosion", "High Real Estate Costs"],
        "grid_factor": 0.79
    },
    "hyderabad": {
        "city": "Hyderabad",
        "risks": ["Drought", "Rapid Urbanization", "Water Scarcity"],
        "grid_factor": 0.82
    }
}

def get_location_key(location: str) -> str:
    location_lower = location.lower()
    if "bangalore" in location_lower or "bengaluru" in location_lower:
        return "bangalore"
    elif "mumbai" in location_lower:
        return "mumbai"
    elif "hyderabad" in location_lower:
        return "hyderabad"
    return "bangalore"


class PDFReportGenerator:
    """
    Generates PDF reports for Infranomic analytics.
    Supports property reports, executive summaries, and energy reports.
    """
    
    # Brand colors
    PRIMARY_COLOR = colors.HexColor("#6366f1")  # Indigo
    SECONDARY_COLOR = colors.HexColor("#10b981")  # Green
    WARNING_COLOR = colors.HexColor("#f59e0b")  # Amber
    DANGER_COLOR = colors.HexColor("#ef4444")  # Red
    DARK_BG = colors.HexColor("#1e1e2e")
    LIGHT_TEXT = colors.HexColor("#e2e8f0")
    
    def __init__(self, whatsapp_service=None):
        self.whatsapp_service = whatsapp_service
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.PRIMARY_COLOR,
            spaceBefore=15,
            spaceAfter=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.gray
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        ))
    
    def format_currency_inr(self, value: float) -> str:
        """Format value in Indian Rupees."""
        if abs(value) >= 10000000:
            return f"₹{value / 10000000:.2f} Cr"
        elif abs(value) >= 100000:
            return f"₹{value / 100000:.2f} L"
        else:
            return f"₹{value:,.0f}"
    
    def generate_property_report(
        self,
        property_data: Dict[str, Any],
        financials: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
        user_state: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate a PDF report for a single property.
        
        Args:
            property_data: Property information
            financials: Financial calculations
            recommendations: List of recommendations
            user_state: User's override state (if any)
            
        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        story = []
        
        # Title
        story.append(Paragraph(
            "Property Analytics Report",
            self.styles['CustomTitle']
        ))
        
        # Property Name
        story.append(Paragraph(
            property_data.get("name", "Property"),
            self.styles['Heading1']
        ))
        
        story.append(Spacer(1, 10))
        
        # Report metadata
        report_date = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")
        story.append(Paragraph(
            f"Generated: {report_date}",
            self.styles['MetricLabel']
        ))
        
        # User state indicator
        if user_state and user_state.get("closed_floors"):
            closed = user_state.get("closed_floors", [])
            story.append(Paragraph(
                f"⚙️ Custom Configuration: Floors {', '.join(map(str, closed))} closed",
                self.styles['Normal']
            ))
        
        story.append(Spacer(1, 20))
        
        # Property Overview Section
        story.append(Paragraph("Property Overview", self.styles['SectionHeader']))
        
        overview_data = [
            ["Location", property_data.get("location", "N/A")],
            ["Type", property_data.get("type", "N/A")],
            ["Total Floors", str(property_data.get("floors", 0))],
            ["Rooms per Floor", str(property_data.get("rooms_per_floor", 0))],
        ]
        
        if user_state and user_state.get("closed_floors"):
            closed_floors = user_state.get("closed_floors", [])
            active_floors = property_data.get("floors", 0) - len(closed_floors)
            overview_data.append(["Active Floors", str(active_floors)])
            overview_data.append(["Closed Floors", ", ".join(map(str, closed_floors))])
        
        overview_table = Table(overview_data, colWidths=[2*inch, 4*inch])
        overview_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ]))
        story.append(overview_table)
        
        story.append(Spacer(1, 20))
        
        # Financial Summary Section
        story.append(Paragraph("Financial Summary", self.styles['SectionHeader']))
        
        financial_data = [
            ["Metric", "Value"],
            ["Monthly Revenue", self.format_currency_inr(financials.get("revenue", 0))],
            ["Operating Costs", self.format_currency_inr(financials.get("operating_cost", 0))],
            ["Energy Costs", self.format_currency_inr(financials.get("energy_cost", 0))],
            ["Maintenance Costs", self.format_currency_inr(financials.get("maintenance_cost", 0))],
            ["Net Profit", self.format_currency_inr(financials.get("profit", 0))],
            ["Profit Margin", f"{financials.get('margin', 0):.1f}%"],
        ]
        
        financial_table = Table(financial_data, colWidths=[3*inch, 3*inch])
        financial_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        story.append(financial_table)
        
        story.append(Spacer(1, 20))
        
        # Recommendations Section
        if recommendations:
            story.append(Paragraph("Recommendations", self.styles['SectionHeader']))
            
            for i, rec in enumerate(recommendations[:5], 1):
                priority_color = {
                    "high": self.DANGER_COLOR,
                    "medium": self.WARNING_COLOR,
                    "low": self.SECONDARY_COLOR
                }.get(rec.get("priority", "medium"), colors.gray)
                
                story.append(Paragraph(
                    f"<font color='#{priority_color.hexval()[2:]}'>{i}. {rec.get('title', 'Recommendation')}</font>",
                    self.styles['Normal']
                ))
                
                story.append(Paragraph(
                    f"   Impact: {self.format_currency_inr(rec.get('financial_impact', 0))}/month",
                    self.styles['MetricLabel']
                ))
                
                story.append(Spacer(1, 5))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            "Infranomic Decision Copilot - Confidential Report",
            self.styles['MetricLabel']
        ))
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_executive_summary_full(
        self,
        executive_data: Dict[str, Any],
        benchmarks: List[Dict[str, Any]],
        properties: List[Dict[str, Any]]
    ) -> bytes:
        """
        Generate a comprehensive executive summary PDF with all analytics.
        
        Includes:
        - Savings potential
        - Carbon reduction
        - Efficiency gains
        - Top strategic actions
        - Portfolio benchmarking
        - High/low performing properties
        """
        from reportlab.graphics.shapes import Drawing, Rect, String
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=25,
            leftMargin=25,
            topMargin=25,
            bottomMargin=25
        )
        
        story = []
        
        # ==================== TITLE PAGE ====================
        # Gradient-like header bar
        header_data = [[""]]
        header_table = Table(header_data, colWidths=[7.5*inch], rowHeights=[0.8*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#667eea")),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        
        story.append(Spacer(1, 20))
        
        # Main Title
        title_style = ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor("#1e293b"),
            alignment=TA_CENTER,
            spaceAfter=5
        )
        story.append(Paragraph("Executive Summary Report", title_style))
        
        subtitle_style = ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        story.append(Paragraph("Infranomic Decision Copilot - Portfolio Analysis", subtitle_style))
        
        # Report date
        date_style = ParagraphStyle(
            name='DateStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#94a3b8"),
            alignment=TA_CENTER,
            spaceAfter=30
        )
        report_date = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
        story.append(Paragraph(f"Generated: {report_date}", date_style))
        
        # ==================== KEY METRICS SECTION ====================
        story.append(Paragraph("Key Performance Metrics", self.styles['SectionHeader']))
        
        # Colorful metrics boxes
        monthly_savings = executive_data.get('total_projected_monthly_savings', 0)
        annual_savings = executive_data.get('total_projected_annual_savings', 0)
        carbon_reduction = executive_data.get('total_carbon_reduction_kg', 0)
        efficiency_gain = executive_data.get('avg_efficiency_improvement', 0)
        
        metrics_data = [
            [
                self._create_metric_cell("Monthly Savings", self.format_currency_inr(monthly_savings), "#10b981"),
                self._create_metric_cell("Annual Savings", self.format_currency_inr(annual_savings), "#3b82f6"),
            ],
            [
                self._create_metric_cell("Carbon Reduction", f"{carbon_reduction:,.0f} kg CO₂", "#22c55e"),
                self._create_metric_cell("Efficiency Gain", f"+{efficiency_gain:.1f}%", "#8b5cf6"),
            ]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[3.5*inch, 3.5*inch], rowHeights=[1.2*inch, 1.2*inch])
        metrics_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(metrics_table)
        
        story.append(Spacer(1, 20))
        
        # ==================== EXECUTIVE INSIGHT ====================
        insight_text = executive_data.get('executive_insight', 'No insights available.')
        insight_style = ParagraphStyle(
            name='InsightStyle',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor("#334155"),
            backColor=colors.HexColor("#f1f5f9"),
            borderPadding=15,
            leading=16
        )
        
        insight_data = [[Paragraph(f"💡 {insight_text}", insight_style)]]
        insight_table = Table(insight_data, colWidths=[7*inch])
        insight_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ]))
        story.append(insight_table)
        
        story.append(Spacer(1, 25))
        
        # ==================== TOP STRATEGIC ACTIONS ====================
        story.append(Paragraph("🎯 Top Strategic Actions", self.styles['SectionHeader']))
        
        actions = executive_data.get('top_strategic_actions', [])
        if actions:
            action_data = [["#", "Property", "Action", "Type", "Impact"]]
            
            for i, action in enumerate(actions[:5], 1):
                action_data.append([
                    str(i),
                    action.get('property_name', ''),
                    action.get('action', '')[:40] + ('...' if len(action.get('action', '')) > 40 else ''),
                    action.get('type', ''),
                    self.format_currency_inr(action.get('impact', 0))
                ])
            
            action_table = Table(action_data, colWidths=[0.4*inch, 1.5*inch, 2.5*inch, 1*inch, 1.1*inch])
            action_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#6366f1")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(action_table)
        
        story.append(Spacer(1, 25))
        
        # ==================== PORTFOLIO BENCHMARKING ====================
        story.append(Paragraph("📊 Portfolio Benchmarking", self.styles['SectionHeader']))
        
        if benchmarks:
            bench_data = [["Property", "Profit", "Energy", "Sustainability", "Carbon", "Occupancy", "Performance"]]
            
            for b in benchmarks:
                # Determine performance level
                avg_rank = (b.get('profit_rank', 3) + b.get('energy_efficiency_rank', 3) + 
                           b.get('sustainability_score_rank', 3) + b.get('carbon_rank', 3)) / 4
                if avg_rank <= 1.5:
                    performance = "⭐ HIGH"
                elif avg_rank <= 2.5:
                    performance = "● MEDIUM"
                else:
                    performance = "○ LOW"
                
                bench_data.append([
                    b.get('name', '')[:15],
                    f"#{b.get('profit_rank', '-')}",
                    f"#{b.get('energy_efficiency_rank', '-')}",
                    f"#{b.get('sustainability_score_rank', '-')}",
                    f"#{b.get('carbon_rank', '-')}",
                    f"{b.get('occupancy_rate', 0)*100:.0f}%",
                    performance
                ])
            
            bench_table = Table(bench_data, colWidths=[1.3*inch, 0.7*inch, 0.7*inch, 1*inch, 0.7*inch, 0.9*inch, 1.2*inch])
            bench_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(bench_table)
        
        story.append(Spacer(1, 25))
        
        # ==================== PROPERTY PERFORMANCE SUMMARY ====================
        story.append(Paragraph("🏢 Property Performance Summary", self.styles['SectionHeader']))
        
        # Separate high and low performers
        high_performers = []
        low_performers = []
        
        for b in benchmarks:
            avg_rank = (b.get('profit_rank', 3) + b.get('energy_efficiency_rank', 3)) / 2
            prop_summary = {
                'name': b.get('name', ''),
                'location': b.get('location', ''),
                'occupancy': b.get('occupancy_rate', 0) * 100,
                'profit_rank': b.get('profit_rank', '-'),
                'energy_rank': b.get('energy_efficiency_rank', '-')
            }
            
            if avg_rank <= 1.5:
                high_performers.append(prop_summary)
            else:
                low_performers.append(prop_summary)
        
        # High performers table
        if high_performers:
            story.append(Paragraph("✅ High Performing Properties", ParagraphStyle(
                name='HighPerf',
                parent=self.styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor("#10b981"),
                fontName='Helvetica-Bold',
                spaceBefore=10,
                spaceAfter=5
            )))
            
            high_data = [["Property", "Location", "Occupancy", "Profit Rank", "Energy Rank"]]
            for p in high_performers:
                high_data.append([
                    p['name'], p['location'], f"{p['occupancy']:.0f}%",
                    f"#{p['profit_rank']}", f"#{p['energy_rank']}"
                ])
            
            high_table = Table(high_data, colWidths=[1.8*inch, 1.8*inch, 1*inch, 1*inch, 1*inch])
            high_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#10b981")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#d1fae5")),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#ecfdf5")),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(high_table)
        
        # Low performers table  
        if low_performers:
            story.append(Spacer(1, 15))
            story.append(Paragraph("⚠️ Properties Needing Attention", ParagraphStyle(
                name='LowPerf',
                parent=self.styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor("#f59e0b"),
                fontName='Helvetica-Bold',
                spaceBefore=10,
                spaceAfter=5
            )))
            
            low_data = [["Property", "Location", "Occupancy", "Profit Rank", "Energy Rank"]]
            for p in low_performers:
                low_data.append([
                    p['name'], p['location'], f"{p['occupancy']:.0f}%",
                    f"#{p['profit_rank']}", f"#{p['energy_rank']}"
                ])
            
            low_table = Table(low_data, colWidths=[1.8*inch, 1.8*inch, 1*inch, 1*inch, 1*inch])
            low_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f59e0b")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#fef3c7")),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#fffbeb")),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(low_table)
        
        story.append(Spacer(1, 25))
        
        # ==================== SAVINGS BREAKDOWN ====================
        story.append(Paragraph("💰 Savings Potential Breakdown", self.styles['SectionHeader']))
        
        savings_data = [
            ["Category", "Monthly", "Annual", "% of Total"],
            ["Energy Optimization", 
             self.format_currency_inr(monthly_savings * 0.4),
             self.format_currency_inr(annual_savings * 0.4),
             "40%"],
            ["Space Consolidation",
             self.format_currency_inr(monthly_savings * 0.35),
             self.format_currency_inr(annual_savings * 0.35),
             "35%"],
            ["Operational Efficiency",
             self.format_currency_inr(monthly_savings * 0.25),
             self.format_currency_inr(annual_savings * 0.25),
             "25%"],
            ["TOTAL",
             self.format_currency_inr(monthly_savings),
             self.format_currency_inr(annual_savings),
             "100%"]
        ]
        
        savings_table = Table(savings_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
        savings_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#059669")),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#d1fae5")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(savings_table)
        
        # ==================== FOOTER ====================
        story.append(Spacer(1, 30))
        
        footer_style = ParagraphStyle(
            name='FooterStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor("#94a3b8"),
            alignment=TA_CENTER
        )
        story.append(Paragraph(
            "Infranomic Decision Copilot | Confidential Executive Report | © 2026 All Rights Reserved",
            footer_style
        ))
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _create_metric_cell(self, label: str, value: str, color: str) -> Table:
        """Create a colorful metric cell for the dashboard."""
        cell_data = [
            [Paragraph(f"<font color='#64748b' size='9'>{label}</font>", self.styles['Normal'])],
            [Paragraph(f"<font color='{color}' size='18'><b>{value}</b></font>", self.styles['Normal'])]
        ]
        cell_table = Table(cell_data, colWidths=[3.3*inch])
        cell_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor(color)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        return cell_table

    def generate_executive_summary(
        self,
        properties: List[Dict[str, Any]],
        portfolio_metrics: Dict[str, Any],
        user_states: Dict[str, Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate an executive summary PDF for the entire portfolio.
        
        Args:
            properties: List of all properties
            portfolio_metrics: Aggregated portfolio metrics
            user_states: Dict of property_id -> user_state
            
        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        story = []
        user_states = user_states or {}
        
        # Title
        story.append(Paragraph(
            "Executive Summary Report",
            self.styles['CustomTitle']
        ))
        
        report_date = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")
        story.append(Paragraph(
            f"Generated: {report_date}",
            self.styles['MetricLabel']
        ))
        
        story.append(Spacer(1, 20))
        
        # Portfolio Overview
        story.append(Paragraph("Portfolio Overview", self.styles['SectionHeader']))
        
        # Count user overrides
        active_overrides = sum(1 for state in user_states.values() if state.get("closed_floors"))
        
        overview_data = [
            ["Total Properties", str(len(properties))],
            ["Total Portfolio Value", self.format_currency_inr(portfolio_metrics.get("total_revenue", 0))],
            ["Total Profit", self.format_currency_inr(portfolio_metrics.get("total_profit", 0))],
            ["Average Occupancy", f"{portfolio_metrics.get('avg_occupancy', 0):.1f}%"],
            ["Active Optimizations", str(active_overrides)],
        ]
        
        overview_table = Table(overview_data, colWidths=[3*inch, 3*inch])
        overview_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f8fafc")),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        story.append(overview_table)
        
        story.append(Spacer(1, 20))
        
        # Properties Summary
        story.append(Paragraph("Properties Summary", self.styles['SectionHeader']))
        
        prop_data = [["Property", "Location", "Floors", "Status", "Revenue"]]
        
        for prop in properties:
            prop_id = prop.get("property_id", "")
            state = user_states.get(prop_id, {})
            closed = state.get("closed_floors", [])
            
            status = f"✓ Optimized ({len(closed)} closed)" if closed else "Standard"
            
            # Get financials from property
            revenue = portfolio_metrics.get("property_revenues", {}).get(prop_id, 0)
            
            prop_data.append([
                prop.get("name", ""),
                prop.get("location", ""),
                str(prop.get("floors", 0)),
                status,
                self.format_currency_inr(revenue)
            ])
        
        prop_table = Table(prop_data, colWidths=[1.8*inch, 1.2*inch, 0.6*inch, 1.4*inch, 1*inch])
        prop_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        ]))
        story.append(prop_table)
        
        # Footer
        story.append(Spacer(1, 40))
        story.append(Paragraph(
            "PropTech Decision Copilot - Executive Report - Confidential",
            self.styles['MetricLabel']
        ))
        
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_energy_report(
        self,
        property_data: Dict[str, Any],
        energy_metrics: Dict[str, Any],
        user_state: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate an energy savings report PDF.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        story = []
        
        # Title
        story.append(Paragraph(
            "Energy Savings Report",
            self.styles['CustomTitle']
        ))
        
        story.append(Paragraph(
            property_data.get("name", "Property"),
            self.styles['Heading1']
        ))
        
        report_date = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")
        story.append(Paragraph(
            f"Generated: {report_date}",
            self.styles['MetricLabel']
        ))
        
        story.append(Spacer(1, 20))
        
        # Energy Metrics
        story.append(Paragraph("Energy Analysis", self.styles['SectionHeader']))
        
        energy_data = [
            ["Metric", "Value"],
            ["Baseline Energy (kWh/month)", f"{energy_metrics.get('baseline_kwh', 0):,.0f}"],
            ["Current Energy (kWh/month)", f"{energy_metrics.get('current_kwh', 0):,.0f}"],
            ["Energy Reduction", f"{energy_metrics.get('reduction_pct', 0):.1f}%"],
            ["Weekly Savings", self.format_currency_inr(energy_metrics.get('weekly_savings', 0))],
            ["Monthly Savings", self.format_currency_inr(energy_metrics.get('monthly_savings', 0))],
            ["Annual Projection", self.format_currency_inr(energy_metrics.get('annual_savings', 0))],
            ["Carbon Reduction (kg CO₂)", f"{energy_metrics.get('carbon_reduction', 0):,.0f}"],
        ]
        
        energy_table = Table(energy_data, colWidths=[3*inch, 3*inch])
        energy_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (-1, 0), self.SECONDARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        story.append(energy_table)
        
        # Footer
        story.append(Spacer(1, 40))
        story.append(Paragraph(
            "PropTech Decision Copilot - Energy Report - Confidential",
            self.styles['MetricLabel']
        ))
        
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    async def send_pdf_via_whatsapp(
        self,
        phone_number: str,
        pdf_bytes: bytes,
        filename: str,
        message: str = "Here's your report:"
    ) -> Dict[str, Any]:
        """
        Send a PDF report via WhatsApp.
        Note: Twilio WhatsApp requires media to be hosted at a public URL.
        For now, we'll send a message indicating PDF is ready.
        """
        if not self.whatsapp_service:
            return {"success": False, "error": "WhatsApp service not configured"}
        
        # In production, you would upload to cloud storage and send media URL
        # For now, send a text message with report summary
        return self.whatsapp_service.send_whatsapp_message(
            phone_number,
            f"""📄 *Report Generated*

{message}

Note: PDF reports are available in your dashboard.
Log in to download: [Dashboard Link]"""
        )


# Global instance
pdf_generator: Optional[PDFReportGenerator] = None


def init_pdf_generator(whatsapp_service=None) -> PDFReportGenerator:
    """Initialize the global PDF generator."""
    global pdf_generator
    pdf_generator = PDFReportGenerator(whatsapp_service)
    return pdf_generator

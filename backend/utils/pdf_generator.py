"""
PDF generation utility using ReportLab for invoices and estimates.
"""

import io
import os
from decimal import Decimal

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class InvoicePDFGenerator:
    """Generates professional PDF invoices."""

    def __init__(self, invoice):
        self.invoice = invoice
        self.buffer = io.BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Define custom paragraph styles for the PDF."""
        self.styles.add(
            ParagraphStyle(
                name="InvoiceTitle",
                parent=self.styles["Heading1"],
                fontSize=28,
                textColor=colors.HexColor("#2C3E50"),
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=12,
                textColor=colors.HexColor("#2C3E50"),
                spaceBefore=12,
                spaceAfter=6,
                fontName="Helvetica-Bold",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CompanyName",
                parent=self.styles["Normal"],
                fontSize=18,
                textColor=colors.HexColor("#2C3E50"),
                fontName="Helvetica-Bold",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="FieldLabel",
                parent=self.styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#7F8C8D"),
                fontName="Helvetica",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="FieldValue",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#2C3E50"),
                fontName="Helvetica",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="TotalLabel",
                parent=self.styles["Normal"],
                fontSize=12,
                textColor=colors.HexColor("#2C3E50"),
                fontName="Helvetica-Bold",
                alignment=TA_RIGHT,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="GrandTotal",
                parent=self.styles["Normal"],
                fontSize=16,
                textColor=colors.HexColor("#E74C3C"),
                fontName="Helvetica-Bold",
                alignment=TA_RIGHT,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="Notes",
                parent=self.styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#7F8C8D"),
                fontName="Helvetica",
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="StatusBadge",
                parent=self.styles["Normal"],
                fontSize=14,
                textColor=colors.white,
                fontName="Helvetica-Bold",
                alignment=TA_CENTER,
            )
        )

    def _format_currency(self, amount):
        """Format amount with currency symbol."""
        currency = self.invoice.currency
        symbols = {
            "USD": "$",
            "EUR": "\u20ac",
            "GBP": "\u00a3",
            "JPY": "\u00a5",
            "CAD": "CA$",
            "AUD": "A$",
        }
        symbol = symbols.get(currency, currency + " ")
        if currency == "JPY":
            return f"{symbol}{int(amount):,}"
        return f"{symbol}{amount:,.2f}"

    def _build_header(self):
        """Build the invoice header with company and invoice info."""
        elements = []

        profile = getattr(self.invoice.user, "business_profile", None)
        company_name = profile.company_name if profile else settings.COMPANY_NAME
        company_address = profile.address if profile else ""
        company_phone = profile.phone if profile else ""
        company_email = profile.email if profile else ""

        # Company info and invoice title in a table
        company_info = []
        company_info.append(Paragraph(company_name, self.styles["CompanyName"]))
        if company_address:
            for line in company_address.split("\n"):
                company_info.append(Paragraph(line, self.styles["FieldValue"]))
        if company_phone:
            company_info.append(Paragraph(f"Phone: {company_phone}", self.styles["FieldValue"]))
        if company_email:
            company_info.append(Paragraph(f"Email: {company_email}", self.styles["FieldValue"]))

        invoice_info = []
        invoice_info.append(Paragraph("INVOICE", self.styles["InvoiceTitle"]))
        invoice_info.append(
            Paragraph(f"Invoice #: {self.invoice.invoice_number}", self.styles["FieldValue"])
        )
        invoice_info.append(
            Paragraph(
                f"Date: {self.invoice.issue_date.strftime('%B %d, %Y')}",
                self.styles["FieldValue"],
            )
        )
        invoice_info.append(
            Paragraph(
                f"Due Date: {self.invoice.due_date.strftime('%B %d, %Y')}",
                self.styles["FieldValue"],
            )
        )

        status_colors = {
            "draft": "#95A5A6",
            "sent": "#3498DB",
            "viewed": "#F39C12",
            "paid": "#27AE60",
            "overdue": "#E74C3C",
            "cancelled": "#E74C3C",
            "partial": "#F39C12",
        }
        status_color = status_colors.get(self.invoice.status, "#95A5A6")
        invoice_info.append(Spacer(1, 4))
        invoice_info.append(
            Paragraph(
                f'<font color="{status_color}">{self.invoice.get_status_display().upper()}</font>',
                self.styles["FieldValue"],
            )
        )

        header_data = [[company_info, invoice_info]]
        header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ]
            )
        )

        elements.append(header_table)
        elements.append(Spacer(1, 20))
        elements.append(
            HRFlowable(width="100%", thickness=2, color=colors.HexColor("#BDC3C7"))
        )
        elements.append(Spacer(1, 15))

        return elements

    def _build_client_section(self):
        """Build the bill-to client section."""
        elements = []
        client = self.invoice.client

        elements.append(Paragraph("BILL TO", self.styles["SectionHeader"]))
        elements.append(Paragraph(client.name, self.styles["FieldValue"]))

        if client.company:
            elements.append(Paragraph(client.company, self.styles["FieldValue"]))
        if client.address:
            for line in client.address.split("\n"):
                elements.append(Paragraph(line, self.styles["FieldValue"]))
        if client.email:
            elements.append(Paragraph(client.email, self.styles["FieldValue"]))
        if client.phone:
            elements.append(Paragraph(client.phone, self.styles["FieldValue"]))

        elements.append(Spacer(1, 20))
        return elements

    def _build_line_items_table(self):
        """Build the line items table."""
        elements = []

        # Table header
        header = [
            Paragraph("<b>#</b>", self.styles["FieldLabel"]),
            Paragraph("<b>Description</b>", self.styles["FieldLabel"]),
            Paragraph("<b>Qty</b>", self.styles["FieldLabel"]),
            Paragraph("<b>Unit Price</b>", self.styles["FieldLabel"]),
            Paragraph("<b>Tax</b>", self.styles["FieldLabel"]),
            Paragraph("<b>Amount</b>", self.styles["FieldLabel"]),
        ]

        data = [header]
        lines = self.invoice.lines.all().order_by("order")

        for idx, line in enumerate(lines, 1):
            row = [
                Paragraph(str(idx), self.styles["FieldValue"]),
                Paragraph(
                    f"{line.description}"
                    + (f"<br/><font size='8' color='#7F8C8D'>{line.details}</font>" if line.details else ""),
                    self.styles["FieldValue"],
                ),
                Paragraph(str(line.quantity), self.styles["FieldValue"]),
                Paragraph(self._format_currency(line.unit_price), self.styles["FieldValue"]),
                Paragraph(f"{line.tax_rate}%", self.styles["FieldValue"]),
                Paragraph(self._format_currency(line.line_total), self.styles["FieldValue"]),
            ]
            data.append(row)

        col_widths = [0.4 * inch, 2.8 * inch, 0.6 * inch, 1.1 * inch, 0.7 * inch, 1.1 * inch]
        table = Table(data, colWidths=col_widths, repeatRows=1)

        table.setStyle(
            TableStyle(
                [
                    # Header
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    # Body
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("TOPPADDING", (0, 1), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                    # Alternating row colors
                    *[
                        ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F8F9FA"))
                        for i in range(2, len(data), 2)
                    ],
                    # Grid
                    ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#2C3E50")),
                    ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#BDC3C7")),
                    # Alignment
                    ("ALIGN", (2, 0), (2, -1), "CENTER"),
                    ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 15))
        return elements

    def _build_totals_section(self):
        """Build the totals section."""
        elements = []

        totals_data = [
            [
                "",
                Paragraph("Subtotal:", self.styles["TotalLabel"]),
                Paragraph(
                    self._format_currency(self.invoice.subtotal),
                    self.styles["FieldValue"],
                ),
            ],
        ]

        if self.invoice.tax_amount > 0:
            totals_data.append(
                [
                    "",
                    Paragraph("Tax:", self.styles["TotalLabel"]),
                    Paragraph(
                        self._format_currency(self.invoice.tax_amount),
                        self.styles["FieldValue"],
                    ),
                ]
            )

        if self.invoice.discount_amount > 0:
            totals_data.append(
                [
                    "",
                    Paragraph("Discount:", self.styles["TotalLabel"]),
                    Paragraph(
                        f"-{self._format_currency(self.invoice.discount_amount)}",
                        self.styles["FieldValue"],
                    ),
                ]
            )

        totals_data.append(
            [
                "",
                Paragraph("TOTAL:", self.styles["GrandTotal"]),
                Paragraph(
                    self._format_currency(self.invoice.total),
                    self.styles["GrandTotal"],
                ),
            ]
        )

        if self.invoice.amount_paid > 0:
            totals_data.append(
                [
                    "",
                    Paragraph("Amount Paid:", self.styles["TotalLabel"]),
                    Paragraph(
                        self._format_currency(self.invoice.amount_paid),
                        self.styles["FieldValue"],
                    ),
                ]
            )
            totals_data.append(
                [
                    "",
                    Paragraph("Balance Due:", self.styles["GrandTotal"]),
                    Paragraph(
                        self._format_currency(self.invoice.balance_due),
                        self.styles["GrandTotal"],
                    ),
                ]
            )

        totals_table = Table(
            totals_data,
            colWidths=[3.5 * inch, 2 * inch, 1.5 * inch],
        )
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LINEABOVE", (1, -1), (-1, -1), 2, colors.HexColor("#2C3E50")),
                ]
            )
        )

        elements.append(totals_table)
        elements.append(Spacer(1, 30))
        return elements

    def _build_notes_section(self):
        """Build the notes and terms section."""
        elements = []

        if self.invoice.notes:
            elements.append(Paragraph("Notes", self.styles["SectionHeader"]))
            elements.append(Paragraph(self.invoice.notes, self.styles["Notes"]))
            elements.append(Spacer(1, 10))

        if self.invoice.terms:
            elements.append(Paragraph("Terms & Conditions", self.styles["SectionHeader"]))
            elements.append(Paragraph(self.invoice.terms, self.styles["Notes"]))
            elements.append(Spacer(1, 10))

        return elements

    def _build_footer(self):
        """Build the footer section."""
        elements = []
        elements.append(
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#BDC3C7"))
        )
        elements.append(Spacer(1, 8))

        profile = getattr(self.invoice.user, "business_profile", None)
        company_name = profile.company_name if profile else settings.COMPANY_NAME

        footer_style = ParagraphStyle(
            name="Footer",
            parent=self.styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#BDC3C7"),
            alignment=TA_CENTER,
        )
        elements.append(
            Paragraph(
                f"Thank you for your business! | {company_name}",
                footer_style,
            )
        )
        return elements

    def generate(self):
        """Generate the complete PDF and return the buffer."""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=30 * mm,
            leftMargin=30 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        elements = []
        elements.extend(self._build_header())
        elements.extend(self._build_client_section())
        elements.extend(self._build_line_items_table())
        elements.extend(self._build_totals_section())
        elements.extend(self._build_notes_section())
        elements.extend(self._build_footer())

        doc.build(elements)
        self.buffer.seek(0)
        return self.buffer

    def save_to_file(self, filepath):
        """Generate PDF and save to filesystem."""
        pdf_buffer = self.generate()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(pdf_buffer.getvalue())
        return filepath


class EstimatePDFGenerator(InvoicePDFGenerator):
    """Generates professional PDF estimates. Extends invoice PDF with estimate-specific changes."""

    def _build_header(self):
        """Override header to say ESTIMATE instead of INVOICE."""
        elements = []

        profile = getattr(self.invoice.user, "business_profile", None)
        company_name = profile.company_name if profile else settings.COMPANY_NAME
        company_address = profile.address if profile else ""
        company_phone = profile.phone if profile else ""
        company_email = profile.email if profile else ""

        company_info = []
        company_info.append(Paragraph(company_name, self.styles["CompanyName"]))
        if company_address:
            for line in company_address.split("\n"):
                company_info.append(Paragraph(line, self.styles["FieldValue"]))
        if company_phone:
            company_info.append(Paragraph(f"Phone: {company_phone}", self.styles["FieldValue"]))
        if company_email:
            company_info.append(Paragraph(f"Email: {company_email}", self.styles["FieldValue"]))

        estimate_info = []
        estimate_info.append(Paragraph("ESTIMATE", self.styles["InvoiceTitle"]))
        estimate_info.append(
            Paragraph(
                f"Estimate #: {self.invoice.estimate_number}",
                self.styles["FieldValue"],
            )
        )
        estimate_info.append(
            Paragraph(
                f"Date: {self.invoice.issue_date.strftime('%B %d, %Y')}",
                self.styles["FieldValue"],
            )
        )
        if self.invoice.expiry_date:
            estimate_info.append(
                Paragraph(
                    f"Valid Until: {self.invoice.expiry_date.strftime('%B %d, %Y')}",
                    self.styles["FieldValue"],
                )
            )

        header_data = [[company_info, estimate_info]]
        header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ]
            )
        )

        elements.append(header_table)
        elements.append(Spacer(1, 20))
        elements.append(
            HRFlowable(width="100%", thickness=2, color=colors.HexColor("#BDC3C7"))
        )
        elements.append(Spacer(1, 15))

        return elements

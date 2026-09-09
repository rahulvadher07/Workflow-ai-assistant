"""
Payslip PDF generation - only the fields listed in Part 8's spec, no
extra personal/sensitive data.
"""

import io

from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from company.models import Company


def generate_payslip_pdf(payslip):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = []

    company = Company.get_solo()
    employee = payslip.employee
    profile = getattr(employee, "employee_profile", None)

    story.append(Paragraph(company.name, styles["Title"]))
    story.append(Paragraph(f"Payslip - {payslip.period.year}-{payslip.period.month:02d}", styles["Heading2"]))
    story.append(Spacer(1, 10 * mm))

    header_data = [
        ["Employee Name", employee.get_full_name() or employee.username],
        ["Employee ID", profile.employee_code if profile else "-"],
        ["Department", profile.department.name if profile else "-"],
        ["Payroll Month", f"{payslip.period.year}-{payslip.period.month:02d}"],
        ["Approval Status", payslip.get_status_display()],
    ]
    header_table = Table(header_data, colWidths=[60 * mm, 100 * mm])
    header_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8 * mm))

    attendance_data = [
        ["Attendance Summary", ""],
        ["Working Days", str(payslip.working_days)],
        ["Present Days", str(payslip.present_days)],
        ["Leave Days", str(payslip.leave_days)],
        ["Late Days", str(payslip.late_days)],
        ["Total Working Hours", f"{payslip.total_worked_minutes / 60:.2f}"],
        ["Overtime Hours", f"{payslip.overtime_minutes / 60:.2f}"],
    ]
    attendance_table = Table(attendance_data, colWidths=[80 * mm, 80 * mm])
    attendance_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#E8EEF7")),
        ("FONTNAME", (0, 0), (1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
    ]))
    story.append(attendance_table)
    story.append(Spacer(1, 8 * mm))

    salary_data = [
        ["Salary Details", ""],
        ["Basic Salary", f"{payslip.basic_salary}"],
        ["Allowances", f"{payslip.allowances}"],
        ["Overtime Amount", f"{payslip.overtime_amount}"],
        ["Gross Salary", f"{payslip.gross_salary}"],
        ["PF Deduction", f"{payslip.pf_deduction}"],
        ["Other Deductions", f"{payslip.other_deductions}"],
        ["Net Salary", f"{payslip.net_salary}"],
    ]
    salary_table = Table(salary_data, colWidths=[80 * mm, 80 * mm])
    salary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#E8EEF7")),
        ("FONTNAME", (0, 0), (1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
    ]))
    story.append(salary_table)

    doc.build(story)
    buffer.seek(0)

    filename = f"payslip_{employee.id}_{payslip.period.year}_{payslip.period.month:02d}.pdf"
    payslip.pdf_file.save(filename, ContentFile(buffer.read()), save=True)
    return payslip.pdf_file

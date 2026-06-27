import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Import the logic from your other file
from processes import get_calculated_bill_data

def setup_thai_font():
    font_path = "Sarabun-Regular.ttf" 
    if os.path.exists(font_path):
        font_name = "Sarabun-Arabic"
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        return font_name
    else:
        print("Warning: Font file not found, using Helvetica.")
        return "Helvetica"

def create_apartment_bill_pdf(bill_data, output_filename="apartment_bill.pdf"):
    font_name = setup_thai_font()
    doc = SimpleDocTemplate(output_filename, pagesize=letter, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('Title', fontSize=18, leading=22, fontName=font_name)
    address_style = ParagraphStyle('Address', fontSize=10, leading=12, fontName=font_name)
    customer_style = ParagraphStyle('Customer', fontSize=11, spaceBefore=10, spaceAfter=10, fontName=font_name)

    rooms = bill_data.get('rooms', [])
    for idx, room in enumerate(rooms):
        elements.append(Paragraph(bill_data.get('apartment_name', ''), title_style))
        elements.append(Paragraph(bill_data.get('apartment_address', ''), address_style))
        elements.append(Paragraph(f"โทร. {bill_data.get('phone', '')} / อีเมล. {bill_data.get('email', '')}", address_style))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"ลูกค้า (Customer) - ห้อง: {room.get('unit_number', 'N/A')}", customer_style))

        charges_data = [['ลำดับ(#)', 'รายการชำระ (Description)', 'ราคา(Price)']]
        total = 0
# ตรงนี้คือส่วนเดิมในโค้ดคุณ ให้แก้เป็นแบบนี้:
        for i, charge in enumerate(room.get('charges', []), 1):
            desc = charge.get('description', 'N/A')
            
            # บังคับให้เป็น float เพื่อให้ f-string พ่นเลขฮินดูอารบิกออกมา
            try:
                price = float(charge.get('amount', 0))
            except:
                price = 0.0
                
            charges_data.append([str(i), desc, f"{price:,.2f}"])
            total += price
        charges_data.append(['', 'จำนวนเงินรวมทั้งสิ้น (Total amount)', f"{total:,.2f} บาท"])

        table = Table(charges_data, colWidths=[0.8*inch, 4.5*inch, 1.7*inch])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))

        footer_data = [
            [f"ใบแจ้งหนี้ (Invoice): {room.get('invoice_type', 'ต้นฉบับ (Original)')}"],
            [f"เลขที่ (ID): {room.get('invoice_id', 'N/A')}"],
            [f"วันที่ (Date): {room.get('bill_date', 'N/A')}"],
            [f"ห้อง (Room): {room.get('unit_number', 'N/A')}"],
            [f"พนักงาน (Staff): {room.get('staff_name', 'N/A')}"]
        ]
        footer_table = Table(footer_data, colWidths=[6.5*inch])
        footer_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
        ]))
        elements.append(footer_table)

        if idx < len(rooms) - 1:
            elements.append(PageBreak())

    doc.build(elements)
    print(f"PDF created successfully: {output_filename}")


def convert_pdf_menu():
    try:
        from pdf_to_jpeg import convert_pdf_to_jpeg
    except ModuleNotFoundError as error:
        if error.name == "fitz":
            print("Missing dependency: PyMuPDF (fitz).")
            print("Install with: pip install PyMuPDF")
            return
        raise

    default_pdf_path = "apartment_bill.pdf"
    pdf_path = input("Enter PDF file path (press Enter for apartment_bill.pdf): ").strip().strip('"')
    if not pdf_path:
        pdf_path = default_pdf_path

    output_dir = input("Enter output folder (press Enter for default): ").strip().strip('"')
    dpi_input = input("Enter DPI (press Enter for 200): ").strip()
    quality_input = input("Enter JPEG quality 1-100 (press Enter for 95): ").strip()

    try:
        dpi = int(dpi_input) if dpi_input else 200
        quality = int(quality_input) if quality_input else 95
    except ValueError:
        print("DPI and quality must be numbers.")
        return

    try:
        created_files = convert_pdf_to_jpeg(
            Path(pdf_path),
            output_dir=Path(output_dir) if output_dir else None,
            dpi=dpi,
            quality=quality,
        )
    except Exception as error:
        print(f"Conversion failed: {error}")
        return

    print("JPEG files created:")
    for file_path in created_files:
        print(file_path)


def run_drc_menu():
    try:
        from drc import main as drc_main
    except Exception as error:
        print(f"Failed to start DRC: {error}")
        return

    try:
        drc_main()
    except EOFError:
        print("DRC canceled (input ended).")


def run_menu():
    while True:
        print("\nSelect an option:")
        print("1. Create apartment bill PDF")
        print("2. Convert PDF to JPEG")
        print("3. Run DRC")
        print("4. Exit")

        try:
            choice = input("Enter choice: ").strip()
        except EOFError:
            print("\nBye.")
            break

        if choice == "1":
            data = get_calculated_bill_data()
            if data:
                create_apartment_bill_pdf(data, "apartment_bill.pdf")
            else:
                print("Failed to get bill data. Check your JSON files.")
        elif choice == "2":
            convert_pdf_menu()
        elif choice == "3":
            run_drc_menu()
        elif choice == "4":
            print("Bye.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    run_menu()
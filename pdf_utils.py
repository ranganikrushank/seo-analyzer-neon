from weasyprint import HTML

def html_to_pdf(html_content: str, output_path: str):
    HTML(string=html_content).write_pdf(output_path)
"""
pdf_utils.py
─────────────────────────────────────────────────────────────────────
PDF template engine for EduCerts.

Workflow:
  1. extract_pdf_placeholders(pdf_path)
       → Scans every page for {{field}} patterns using PyMuPDF and pdfplumber.
       → Returns: { "field_name": [(page_idx, x0, y0, x1, y1), ...] }

  2. render_pdf_certificate(template_path, field_values, output_path)
       → Overlays field values on top of extracted positions.

  3. apply_signatures_to_pdf(...)
       → Overlays images on top of reserved signature/stamp placeholders.
"""

import re
import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path

# More robust regex to handle potential line breaks or weird spacing inside {{ }}
PLACEHOLDER_RE = re.compile(r"\{\{\s*([\w]+)\s*\}\}")

# ──────────────────────────────────────────────────────────────────
# 1) Extract placeholders + their bounding boxes from a PDF template
# ──────────────────────────────────────────────────────────────────

def extract_pdf_placeholders(pdf_path: str) -> dict:
    """
    Ultra-robust extraction of placeholders from:
    1. Text layer: {{field_name}}
    2. Interactive Form Fields (AcroForms): Field Names
    """
    result: dict[str, list] = {}
    doc = fitz.open(pdf_path)

    for page_idx, page in enumerate(doc):
        # --- PASS 1: Interactive Form Fields (AcroForms) ---
        for widget in page.widgets():
            field_name = widget.field_name
            if field_name:
                if field_name not in result:
                    result[field_name] = []
                # Store widget position; we can fill it directly later
                result[field_name].append({
                    "type": "acroform",
                    "page": page_idx,
                    "rect": (widget.rect.x0, widget.rect.y0, widget.rect.x1, widget.rect.y1)
                })

        # --- PASS 2: Text Layer ({{placeholder}}) ---
        words = page.get_text("words")
        if words:
            full_text = ""
            index_map = []
            for w in words:
                word_str = w[4]
                for _ in range(len(word_str)):
                    index_map.append(w)
                full_text += word_str + " "
                index_map.append(None)

            for match in PLACEHOLDER_RE.finditer(full_text):
                field_name = match.group(1)
                start, end = match.start(), match.end()
                participating_words = [index_map[k] for k in range(start, end) if index_map[k] is not None]
                
                if participating_words:
                    x0 = min(w[0] for w in participating_words)
                    y0 = min(w[1] for w in participating_words)
                    x1 = max(w[2] for w in participating_words)
                    y1 = max(w[3] for w in participating_words)
                    
                    if field_name not in result:
                        result[field_name] = []
                    result[field_name].append({
                        "type": "text_overlay",
                        "page": page_idx,
                        "rect": (x0, y0, x1, y1)
                    })

    doc.close()
    return result


# ──────────────────────────────────────────────────────────────────
# 2) Render a certificate PDF by overlaying values on the template
# ──────────────────────────────────────────────────────────────────

def render_pdf_certificate(
    template_path: str,
    field_values: dict,
    output_path: str,
    signature_img_path: str | None = None,
    stamp_img_path: str | None = None,
) -> str:
    """
    Fills forms and overlays text/images on the PDF.
    """
    placeholder_map = extract_pdf_placeholders(template_path)
    doc = fitz.open(template_path)
    IMAGE_FIELDS = {"digital_signature", "stamp"}

    for field_name, occurrences in placeholder_map.items():
        value = field_values.get(field_name, "")
        is_image_field = field_name in IMAGE_FIELDS

        for occ in occurrences:
            page = doc[occ["page"]]
            rect = fitz.Rect(occ["rect"])
            
            if occ["type"] == "acroform":
                # DO NOT erase for AcroForms - the widget will overlay naturally
                # Fill the existing widget
                for widget in page.widgets():
                    if widget.field_name == field_name:
                        if is_image_field:
                            img_path = signature_img_path if field_name == "digital_signature" else stamp_img_path
                            if img_path and Path(img_path).exists():
                                page.insert_image(rect, filename=img_path)
                        else:
                            widget.field_value = str(value)
                            widget.update()
            else:
                # --- ERASE THE PLACEHOLDER FOR TEXT LAYER ONLY ---
                # We use overlay=True to draw on top of the text layer.
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)

                # Text overlay logic
                if is_image_field:
                    img_path = signature_img_path if field_name == "digital_signature" else stamp_img_path
                    if img_path and Path(img_path).exists():
                        page.insert_image(rect, filename=img_path)
                else:
                    if value:
                        # Font size: cap at box height, default 11 for standard look
                        font_size = min(rect.height * 0.9, 14)
                        # Pixel-perfect alignment: place at original x0, with baseline adjusted
                        page.insert_text(
                            point=fitz.Point(rect.x0, rect.y1 - (rect.height * 0.15)),
                            text=str(value),
                            fontsize=font_size,
                            color=(0, 0, 0),
                        )

    # Flatten the form (makes it uneditable and professional)
    doc.need_appearances(True) # Ensure values are visible
    # doc.save(output_path, incremental=False, encryption=fitz.PDF_ENCRYPT_KEEP)
    doc.save(output_path)
    doc.close()
    return output_path


# ──────────────────────────────────────────────────────────────────
# 3) Apply signature/stamp to an *already-rendered* certificate PDF
# ──────────────────────────────────────────────────────────────────

def apply_signatures_to_pdf(
    pdf_path: str,
    signature_img_path: str | None,
    stamp_img_path: str | None,
    template_path: str,
    output_path: str,
) -> str:
    """
    Applies images to an already rendered PDF.
    """
    placeholder_map = extract_pdf_placeholders(template_path)
    doc = fitz.open(pdf_path)

    for field_name, occurrences in placeholder_map.items():
        img_path = None
        if field_name == "digital_signature":
            img_path = signature_img_path
        elif field_name == "stamp":
            img_path = stamp_img_path
        
        if not img_path or not Path(img_path).exists():
            continue

        for occ in occurrences:
            page = doc[occ["page"]]
            rect = fitz.Rect(occ["rect"])
            # Erase existing placeholder text/blank space
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
            page.insert_image(rect, filename=img_path)

    doc.save(output_path)
    doc.close()
    return output_path
